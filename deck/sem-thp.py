#!/usr/bin/env python3
"""sem-thp.py <programa> [args]: desliga as huge pages transparentes só para este processo e os filhos
(prctl PR_SET_THP_DISABLE, que passa pelo exec) e executa o programa."""
import ctypes, os, sys
if ctypes.CDLL(None, use_errno=True).prctl(41, 1, 0, 0, 0) != 0:
    print("sem-thp: prctl falhou, errno", ctypes.get_errno(), file=sys.stderr)
os.execvp(sys.argv[1], sys.argv[1:])
