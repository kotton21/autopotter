#!/usr/bin/env python3
"""Brief tester for SimpleLogger"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from autopotter_tools.simplelogger import Logger

class ClassA:
    def method_a(self):
        Logger.info("Message from ClassA.method_a")
        Logger.warning("Warning from ClassA.method_a")

class ClassB:
    def method_b(self):
        Logger.debug("Debug from ClassB.method_b")
        Logger.error("Error from ClassB.method_b")

def standalone_function():
    Logger.info("Message from standalone_function")
    Logger.debug("Critical from standalone_function")

if __name__ == "__main__":
    Logger.info("Direct call from main script")
    
    standalone_function()
    
    a = ClassA()
    a.method_a()

    Logger.setup(loglevel='DEBUG')
    
    b = ClassB()
    b.method_b()
    
    Logger.info("Test complete")

