import sys
p = sys.argv[1]
s = open(p).read()
old_linux = """#else
// (linux: no structured exceptions; the driver is called as it is)
VkResult guarded_graphics(VkPipelineCache cache, const VkGraphicsPipelineCreateInfo* ci, VkPipeline* pl) {
    return vkCreateGraphicsPipelines(dev.device, cache, 1, ci, nullptr, pl);
}
VkResult guarded_compute(VkPipelineCache cache, const VkComputePipelineCreateInfo* ci, VkPipeline* pl) {
    return vkCreateComputePipelines(dev.device, cache, 1, ci, nullptr, pl);
}
#endif"""
new_linux = r"""#else
// (steamdeck) linux: the driver's compiler crashing on one shader (RADV on the Deck, Mesa 26.2: a write at 0x40 in
// libvulkan_radeon.so) costs that pipeline, not the game, as __try does on Windows. A SIGSEGV/SIGBUS on a thread inside
// a guarded call jumps back out; any other goes on to the handler before ours. The program is added to RX_VK_SKIP_FILE,
// so its draws are left out now and at every later start.
thread_local sigjmp_buf* guard_jb = nullptr;
struct sigaction guard_prev[32];
void guard_on_signal(int sig, siginfo_t* si, void* uc) {
    if (sigjmp_buf* jb = guard_jb) {
        guard_jb = nullptr;
        siglongjmp(*jb, 1);
    }
    const struct sigaction* p = &guard_prev[sig];
    if ((p->sa_flags & SA_SIGINFO) && p->sa_sigaction) { p->sa_sigaction(sig, si, uc); return; }
    if (p->sa_handler != SIG_IGN && p->sa_handler != SIG_DFL && p->sa_handler) { p->sa_handler(sig); return; }
    signal(sig, SIG_DFL);
}
void guard_install() {   // (ours in front, again if someone installed theirs after us)
    static std::mutex mu;
    for (int sig : {SIGSEGV, SIGBUS}) {
        struct sigaction cur;
        sigaction(sig, nullptr, &cur);
        if ((cur.sa_flags & SA_SIGINFO) && cur.sa_sigaction == guard_on_signal) continue;
        std::lock_guard lk(mu);
        sigaction(sig, nullptr, &cur);
        if ((cur.sa_flags & SA_SIGINFO) && cur.sa_sigaction == guard_on_signal) continue;
        struct sigaction sa;
        memset(&sa, 0, sizeof sa);
        sa.sa_sigaction = guard_on_signal;
        sa.sa_flags = SA_SIGINFO | SA_NODEFER;
        sigemptyset(&sa.sa_mask);
        sigaction(sig, &sa, &guard_prev[sig]);
    }
}
void guard_fault(const char* what) {
    const uint64_t k = guard_key;
    logf("vk: the driver crashed building the %s pipeline of %016llx: left out (RX_VK_SKIP_FILE)", what, (unsigned long long)k);
    if (const char* path = getenv("RX_VK_SKIP_FILE"); path && *path && k)
        if (FILE* f = fopen(path, "ab")) fprintf(f, "%016llx\n", (unsigned long long)k), fclose(f);
}
__attribute__((noinline)) VkResult guarded_graphics(VkPipelineCache cache, const VkGraphicsPipelineCreateInfo* ci, VkPipeline* pl) {
    guard_install();
    sigjmp_buf jb;
    if (sigsetjmp(jb, 1)) {
        guard_fault("graphics");
        *pl = VK_NULL_HANDLE;
        return (VkResult)-77;
    }
    guard_jb = &jb;
    const VkResult r = vkCreateGraphicsPipelines(dev.device, cache, 1, ci, nullptr, pl);
    guard_jb = nullptr;
    return r;
}
__attribute__((noinline)) VkResult guarded_compute(VkPipelineCache cache, const VkComputePipelineCreateInfo* ci, VkPipeline* pl) {
    guard_install();
    sigjmp_buf jb;
    if (sigsetjmp(jb, 1)) {
        guard_fault("compute");
        *pl = VK_NULL_HANDLE;
        return (VkResult)-77;
    }
    guard_jb = &jb;
    const VkResult r = vkCreateComputePipelines(dev.device, cache, 1, ci, nullptr, pl);
    guard_jb = nullptr;
    return r;
}
#endif"""
assert s.count(old_linux) == 1, "linux block"
s = s.replace(old_linux, new_linux)
reps = [
    ("    const VkResult r = guarded_graphics(part >= 0 || driver_cache_only ? VK_NULL_HANDLE : pcache, &ci, &pl);",
     "    GUARD_KEY(p.key);\n    const VkResult r = guarded_graphics(part >= 0 || driver_cache_only ? VK_NULL_HANDLE : pcache, &ci, &pl);"),
    ("        if (guarded_compute(pcache, &ci, &pl) == VK_SUCCESS && pl) {",
     "        GUARD_KEY(p.key);\n        if (guarded_compute(pcache, &ci, &pl) == VK_SUCCESS && pl) {"),
    ("                if (const VkResult r = guarded_compute(pcache, &ci, &made); r != VK_SUCCESS || !made) {",
     "                GUARD_KEY(q.key);\n                if (const VkResult r = guarded_compute(pcache, &ci, &made); r != VK_SUCCESS || !made) {"),
    ("        if (const VkResult made = guarded_compute(pcache, &ci, &p.compute_pipeline); made != VK_SUCCESS) {",
     "        GUARD_KEY(p.key);\n        if (const VkResult made = guarded_compute(pcache, &ci, &p.compute_pipeline); made != VK_SUCCESS) {"),
]
for a, b in reps:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
# includes and the thread-local key, global (outside the file's namespaces)
anchor = '#include "vk_paths.h"'
head = anchor + """
#ifdef _WIN32
#define GUARD_KEY(k) ((void)0)
#else
#include <setjmp.h>
#include <signal.h>
static thread_local uint64_t guard_key = 0;   // (steamdeck) the program a guarded pipeline call is building
#define GUARD_KEY(k) (guard_key = (k))
#endif"""
assert s.count(anchor) == 1
s = s.replace(anchor, head, 1)
open(p, "w").write(s)
print("ok")
