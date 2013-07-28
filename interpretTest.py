#!/usr/bin/python

import nltk
import re

#sent =['always not room1 and room2'] #ambiguous safety
sent = ['if you are not in room1 and activating dig then go to room2'] #conditional
#sent = ['if you are not in room1 or room2 then go to room2']
#sent = ['go to room1 and room2'] #ambiguous liveness
#sent = ['go to room1 and stay']
#sent = ['group myGroup is room1, room2','if you are in any myGroup then do dig'] #region groups with 'any'
#sent = ['group myGroup is room1, room2','go to all myGroup'] #region groups with 'all'
#sent = ['mem1 is set on room2 and reset on beep'] #memory proposition
#sent = ['mem1 is toggled on beep'] #memory toggle

regions = ['room1','room2','room3']
actions = ['dig','beep']
sensors = ['door1','door2']
auxProps = ['mem1', 'mem2']
groups = {}

spec = []

def main():
    #Open CFG file
    grammarFile = open('grammar1.fcfg')
    grammarText = grammarFile.read()
    
    #Add production rules for region names to our grammar string
    for region in regions:
        grammarText += '\nREGION[SEM=<'+region+'>] -> \''+region+'\''
    
    #Add production rules for action names to our grammar string
    for action in actions:
        grammarText += '\nACTION[SEM=<'+action+'>] -> \''+action+'\''
    
    #Add production rules for sensor names to our grammar string
    for sensor in sensors:
        grammarText += '\nSENSOR[SEM=<'+sensor+'>] -> \''+sensor+'\''
        
    #Add production rules for auxilliary propositions to our grammar string
    for prop in auxProps:
        grammarText += '\nAUXPROP[SEM=<'+prop+'>] -> \''+prop+'\''
    
    #Generate regular expression to match sentences defining region groups
    #Resultant expression is: 'group (\w+) is (?:(region1),? ?|(region2),? ?|(region3),? ?)+'
    groupDefPattern = 'group (\w+) is (?:'
    for region in regions:
        groupDefPattern += '(' + region + '),? ?|'
    groupDefPattern = groupDefPattern[0:-1]
    groupDefPattern += ')+'
    r_groupDef = re.compile(groupDefPattern)
    
    #Generate NLTK feature grammar object from grammar string
    grammar = nltk.grammar.parse_fcfg(grammarText)
    
    for inputString in sent:
        print inputString
        #Examine input to find any group definitons
        m_groupDef = r_groupDef.match(inputString)
        if m_groupDef:
            #Add semantics of group to our grammar string
            groupName = m_groupDef.groups()[0]
            grammarText += '\nGROUP[SEM=<' + groupName + '>] -> \'' + groupName + '\''
            #Add specified regions to our dictionary of groups
            groups[groupName] = filter(lambda x: x != None, m_groupDef.groups()[1:])
            print 'Groups updated: ' + str(groups)
            #Re-compile grammar
            grammar = nltk.grammar.parse_fcfg(grammarText)
            continue
        
        #Parse input string using grammar
        result = nltk.sem.batch_interpret([inputString], grammar, u'SEM', 2)[0]
        
        nTrees = 0;
        for (syntree, semstring) in result:
            if spec.count(semstring) != 0:
                continue
            spec.append(semstring)
            nTrees += 1
            #Expand 'stay' phrases
            semstring = parseStay(str(semstring))
            #Expand region groups, 'any' and 'all'
            semstring = parseGroupAny(semstring, syntree)
            semstring = parseGroupAll(semstring, syntree)
            #Expand memory propositions
            semstring = parseMemory(semstring, syntree)
            semstring = parseToggle(semstring, syntree)
            print
            print 'Syntax tree ' + str(nTrees) + ': '
            print syntree.pprint()
            print
            print 'Formula result ' + str(nTrees) + ': '
            print semstring
            print
            
        if nTrees == 0:
            print 'No valid parse found!'

def parseStay(semstring):
    def appendStayClause(ind):
        if ind == len(regions) - 1:
            return 'Iff(Next('+regions[ind]+'),'+regions[ind]+')'
        else:
            return 'And(Iff(Next('+regions[ind]+'),'+regions[ind]+'),'+appendStayClause(ind+1)+')'
    if semstring.find('$stay') != -1:       
        stay = appendStayClause(0)
        return semstring.replace('$stay',stay)
    else:
        return semstring

def parseGroupAll(semstring, syntree):
    def appendAllClause(semstring, ind, groupRegions):
        if ind == len(groupRegions) - 1:
            return re.sub('\$All\(\w+\)',groupRegions[ind],semstring)
        else:
            return 'And('+re.sub('\$All\(\w+\)',groupRegions[ind],semstring)+','+appendAllClause(semstring, ind+1, groupRegions)+')'
    if semstring.find('$All') == -1:
        return semstring
    else:
        groupName = re.search('\$All\((\w+)\)',semstring).groups()[0]
        return appendAllClause(semstring, 0, groups[groupName])
    
def parseGroupAny(semstring, syntree):
    def appendAnyClause(ind, groupRegions):
        if ind == len(groupRegions) - 1:
            return groupRegions[ind]
        else:
            return 'Or('+groupRegions[ind]+','+appendAnyClause(ind+1, groupRegions)+')'
    if semstring.find('$Any') != -1:
        groupName = re.search('\$Any\((\w+)\)',semstring).groups()[0]
        groupRegions = groups[groupName]
        anyClause = appendAnyClause(0, groupRegions)
        return re.sub('\$Any\('+groupName+'\)', anyClause, semstring)
    else:
        return semstring
        
def parseMemory(semstring, syntree):
    if semstring.find('$Mem') != -1:
        m_Mem = re.search('\$Mem\((.*),(.*),(.*)\)',semstring)
        phi_m = m_Mem.groups()[0]
        phi_s = m_Mem.groups()[1]
        phi_r = m_Mem.groups()[2]
        setClause = 'Glob(Imp(And('+phi_s+',Not('+phi_r+')),Next('+phi_m+')))'
        resetClause = 'Glob(Imp('+phi_r+',Not(Next('+phi_m+'))))'
        holdOnClause = 'Glob(Imp(And('+phi_m+',Not('+phi_r+')),Next('+phi_m+')))'
        holdOffClause = 'Glob(Imp(And(Not('+phi_m+'),Not('+phi_s+')),Not(Next('+phi_m+'))))'
        if phi_r == 'false':
            #Generate memory statement with no reset
            semstring = 'And('+setClause+','+holdOnClause+')'
        else:
            #Generate memory statement with reset
            semstring = 'And('+setClause+',And('+resetClause+',And('+holdOnClause+','+holdOffClause+')))'
    return semstring
    
def parseToggle(semstring, syntree):
    if semstring.find('$Tog') != -1:
        m_Tog = re.search('\$Tog\((.*),(.*)\)',semstring)
        phi_m = m_Tog.groups()[0]
        phi_t = m_Tog.groups()[1]
        turnOffClause = 'Glob(Imp(And('+phi_m+','+phi_t+'),Not(Next('+phi_m+'))))'
        turnOnClause = 'Glob(Imp(And(Not('+phi_m+'),'+phi_t+'),Next('+phi_m+')))'
        holdOnClause = 'Glob(Imp(And('+phi_m+',Not('+phi_t+')),Next('+phi_m+')))'
        holdOffClause = 'Glob(Imp(And(Not('+phi_m+'),Not('+phi_t+')),Not(Next('+phi_m+'))))'
        semstring = 'And('+turnOnClause+',And('+turnOffClause+',And('+holdOnClause+','+holdOffClause+')))'
    return semstring

if __name__ == "__main__":
    main()
