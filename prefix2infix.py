#!/usr/bin/python

import re

def prefixFOL2InfixLTL(prefixString):
    andGroups = re.match('And\((.*),(.*)\)', prefixString)    
    orGroups = re.match('Or\((.*),(.*)\)', prefixString)
    notGroups = re.match('Not\((.*)\)', prefixString)
    nextGroups = re.match('Next\((.*)\)', prefixString)
    globallyGroups = re.match('globally\((.*)\)', prefixString)
    globallyFinallyGroups = re.match('globallyFinally\((.*)\)', prefixString)
    
    if andGroups:
        return prefixFOL2InfixLTL(andGroups.group(1)) + '/\\' + prefixFOL2InfixLTL(andGroups.group(2))
    else if orGroups:
        
    
