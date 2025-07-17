#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys

# Add the "libs" subdirectory to the Python module search path
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "libs"))

import zignode  # Import the custom zignode module (zignode.py)

# ────────────────[ Custom functions shared by this node ]────────────────

def my_custom_function(text):
    """
    Example function that prints and returns a formatted message.
    
    Args:
        text (str): Input string to be included in the response.
    
    Returns:
        str: A formatted response string.
    """
    response = f"Executing my_custom_function with: {text}"
    print(response)
    return response

def test_function_01(arg):
    """
    Test function that passes its argument to the zignode.frame method.
    
    Args:
        arg (Any): Argument to be passed to zignode.frame.
    
    Returns:
        Any: The same argument, unchanged.
    """
    zignode.frame(arg)
    return arg

# ────────────────[ End of user-defined functions ]──────────────────────

# Manual list of node IP addresses and ports (if you want to override LAN scanning)
my_manual_nodes = [
    ('192.168.0.1', 8635),
    ('somehost', 8636),
    ('otherhost', 8637)
]

if __name__ == '__main__':
    # Start the ZigNode instance with user-defined functions and optional parameters.
    # - external_locals: provides access to the defined functions
    # - manual_node_list: specifies target nodes explicitly
    # - debug_mode: enables verbose output for troubleshooting
    zignode.auto(
        external_locals=locals(),
        manual_node_list=my_manual_nodes,
        debug=True
    )

# Notes:
# - If manual_node_list is omitted, zignode will scan the local network (IPv4, < /16).
# - 'zignode.auto()' is the minimal required call to activate the node functionality.
