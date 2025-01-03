#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "libs"))
import zignode

# ─────────────────────────────────────────────────────────────────────────────────────────┤ Functions Specific ├────────────


def test_function_01(arg):
    zignode.frame(arg)
    return arg


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Functions Specific ├────────────
if __name__ == "__main__":
    zignode.auto(locals())
