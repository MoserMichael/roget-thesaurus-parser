""" Parses the roget thesaurus and makes it accessible through an API.
"""
import sys
import re
import os
import time

__all__ = [ 'RogetBuilder', 'RogetThesaurus', 'RogetNode', 'Sense', 'HeadWord', 'RogetThesaususFormatterText', 'RogetThesaurusFormatterXML', 'ROGET_NODE_CATEGORY', 'ROGET_NODE_HEADWORD', 'ROGET_NODE_SENSE_GROUP', 'ROGET_NODE_SENSE', 'WORD_TYPE_NONE', 'WORD_TYPE_VERB', 'WORD_TYPE_NOUN', 'WORD_TYPE_ADJ', 'WORD_TYPE_ADVERB', 'WORD_TYPE_PHRASE' ]



try:
    import cPickle as pickle
except Exception:
    print( 'failed to load cPicle' )

""" types of nodes in tree """
ROGET_NODE_CATEGORY = 1
ROGET_NODE_HEADWORD = 2
ROGET_NODE_SENSE_GROUP = 4
ROGET_NODE_SENSE     = 8


""" types of words """
WORD_TYPE_NONE = 0
WORD_TYPE_VERB = 1
WORD_TYPE_NOUN = 2
WORD_TYPE_ADJ  = 3
WORD_TYPE_ADVERB  =  4
WORD_TYPE_PHRASE = 5

""" last counter of nodes """
_lastInternalId = 1



class RogetBuilder:
    """
        The main entry point of this library; builds an instances of RogetThesaurus
    """
    _RECURSION_LIMIT = 4500
    _VERBOSE = 1

    #_wordGroupBoundaryRe = re.compile( '((\&amp;c\s+(\([^\)]+\))?\s*[^\s\,\;]+\.?|\[[^]]+\]|[^;])+)' )
    _wordGroupBoundaryRe = re.compile( r'((\&amp;c\s+(\([^\)]+\))?\s*[^\s^\,^\;^\.]+|\[[^]]+\]|\.(?!\n)|[^\;^\.])+)' )
    _wordBoundaryRe = re.compile( r'((\&amp;c\s+(\([^\)]+\))?\s*[^\s^\,^\;^\.]+\.?|\[[^]]+\]|[^,])+)' )
    _startHeadWordRe = re.compile(r"^\s*([0-9]+[a-z]*)?.\s*(\[[^\]]*\])?([^\-]+)\-")
    _linkRe = re.compile( r'\&amp;c\s+(\([^\)]+\))?\s*([^\s^\,^\;^\.]+)\.?' )
    _commentRe = re.compile(r'\[([^\]]*)\]')
    _attributeRe = re.compile(r'(N\.|Adj\.|Adv\.|V\.|Phr\.)')
    _cleanupRe = re.compile(r'[\^\n]')
    _cleanupRe2 = re.compile(r'\s\s+')
    _numRe = re.compile(r'(\d+)')

    _headWordIndex = {}
    _senseIndex = {}
    _lastHeadIndex  = None

    def __init__(self, verbose = 0):
        self._VERBOSE = verbose

    def _resolveReference( self, node ):
        if node.type == ROGET_NODE_HEADWORD or node.type == ROGET_NODE_SENSE:
            if node.link != None:
                if not node._link in self._headWordIndex:
                    raise Exception("word: " + node.key   + " unresolved link: " + str( node.link ) )
                node._link = self._headWordIndex[ node._link ]

        if node._type == ROGET_NODE_HEADWORD or node._type == ROGET_NODE_SENSE:
            if node.key == '' and node.link != None:
                node._key = node._link._key
            if node._key not in self._senseIndex:
                self._senseIndex[ node._key ] = []
            self._senseIndex[ node._key ].append( node )

        for n  in node.child:
            self._resolveReference( n )

    def _parseWord(self, word, text ):
        textCopy = text

        n = self._commentRe.search( text )
        if n:
            commentText = n.group(1).strip()
            if self._cleanupRe.search( commentText ):
                commentText = self._cleanupRe.sub( '', commentText )
            word._comment = commentText.strip()
            text = self._commentRe.sub( '', text )
        n = self._linkRe.search( text )
        if n:
            attribValue = n.group(1)
            linkValue = n.group(2)

            if attribValue == None and linkValue == None:
                raise Exception('Bad link: ' + text)

            if attribValue == None:
                attribValue = linkValue
                linkValue = None

            if attribValue != None:
                lowerAttrib = attribValue.lower()
                if lowerAttrib == 'adj' or  lowerAttrib == 'adj.':
                    word._wordType = WORD_TYPE_ADJ
                elif lowerAttrib == 'v' or lowerAttrib == 'v.':
                    word._wordType = WORD_TYPE_VERB
                elif lowerAttrib == 'adv' or lowerAttrib == 'adv.':
                    word._wordType  = WORD_TYPE_ADVERB
                elif lowerAttrib == 'n':
                    word._wordType = WORD_TYPE_NOUN
                elif lowerAttrib == 'phr':
                    word._wordType = WORD_TYPE_PHRASE
                elif lowerAttrib[0].isdigit():
                    linkValue = lowerAttrib

            if linkValue != None:
                word._link = linkValue.strip()
            text = self._linkRe.sub( '', text)

        n = self._attributeRe.search( text )
        if n:
            val = n.group(1)
            if val == 'V.':
                word._wordType = WORD_TYPE_VERB
            elif val == 'N.':
                word._wordType = WORD_TYPE_NOUN
            elif val == 'Adj.':
                word._wordType = WORD_TYPE_ADJ
            elif val == 'Adv.':
                word._wordType = WORD_TYPE_ADVERB
            elif val == 'Phr.':
                word._wordType = WORD_TYPE_PHRASE
            else:
                raise Exception(val + " -- " + text)
            text = self._attributeRe.sub( '', text )

        #n = self.linkType2.search( text )
        #if n:
        #    # TODO: extract link type
        #    text = self.linkType2.sub( '', text )

        if self._cleanupRe.search( text ):
            text = self._cleanupRe.sub( ' ', text )

        if self._cleanupRe2.search( text ):
            text = self._cleanupRe2.sub( ' ', text )

        word._key = text.strip()

        if word._key == '' and word.link == '':
            raise Exception('empty word : ' + textCopy)
        #print( word.key )

    def _parseHeadWords(self, node, passage ):

        #match = self._startHeadWordRe.match( passage )
        matchPos = passage.find('--')
        if matchPos != -1:
            try:
                matchPos += 1
                headDef = passage[ :matchPos ]
                match = self._startHeadWordRe.match( headDef )
                if match:
                    headWord = HeadWord( match.group(1), node )
                    self._parseWord( headWord, match.group(3) )

                    if match.group(2) != None:
                        headWord._linkComment = match.group(2).strip()

                    matchPos += 1
                    passage = passage[ matchPos: ]

                    self._headWordIndex[ headWord.index ] = headWord

                    n = self._numRe.match( headWord.index )
                    if n != None:
                        if self._lastHeadIndex != None and (int(n.group(1)) - int(self._lastHeadIndex)) > 1:
                            raise Exception('last index ' + self._lastHeadIndex + 'current index: ' + n.group(1) )
                        self._lastHeadIndex = n.group(1)

                    #parse word groups
                    groups = self._wordGroupBoundaryRe.findall( passage )
                    for g in groups:
                        gr = g[0].strip()
                        if gr =='':
                            continue
                        #print( '->', gr )
                        wgroup = re.findall( self._wordBoundaryRe, gr )
                        if  len(wgroup) > 1:
                            relatedWords = RogetNode( ROGET_NODE_SENSE_GROUP, None, headWord)
                            for wg in wgroup:
                                w = Sense( ROGET_NODE_SENSE, relatedWords )
                                self._parseWord( w, wg[0] )
                        else:
                            w  = Sense( ROGET_NODE_SENSE, headWord )
                            for wg in wgroup:
                                self._parseWord( w, wg[0] )

                        #for w in wgroup:
                        #    print "\t\t$" , w[0] , "$"

            except Exception:
                print('Error during pasing: ', passage)
                raise

    def parse(self):
        """
            parse the roget thesaursus
            returns an instance of RogetThesaurus

            Note that that file 10681-body.txt  must be in the same directory as the script roget.py
        """
        

        rpath = os.path.join(os.path.dirname(__file__), '10681-body.py' )
        if os.access( rpath, os.F_OK | os.R_OK ) ==  0:
            raise Exception("Roget thesaursus text file rpath has not been found")

        if self._VERBOSE != 0:
            print("parsing file: ", rpath)
            tm = time.time()

        root = RogetNode(ROGET_NODE_CATEGORY, 'root')
        classMatch = re.compile("^CLASS")
        divisionMatch = re.compile("^DIVISION")
        sectionMatch = re.compile("^SECTION")
        subsectionMatch = re.compile(r"^[0-9]+\.? [A-Z][A-Z,\s]+")

        currentNode = None
        currentClass = None
        currentDivision = None
        currentSection = None
        currentSubSection = None

        passage = ''
        passageLines = 0

        with open( rpath ) as f:
            for line in f:
                if line.strip() != '':
                    passage += line
                    passageLines += 1
                elif line.strip() == '':
                    if 'End of of E-Thesaurus' in passage:
                        break

                    if classMatch.match( passage ):
                        lines = passage.split('\n')

                        currentNode = RogetNode( ROGET_NODE_CATEGORY, lines[0], root )
                        currentNode._key = lines[1].strip()
                        currentClass = currentNode
                        currentDivision = None
                        currentSection = None
                        currentSubSection = None

                    elif divisionMatch.match( passage ):
                        lines = passage.split( '\n' )
                        currentNode = RogetNode( ROGET_NODE_CATEGORY, lines[0], currentClass )
                        currentNode._key = lines[1].strip()
                        currentDivision = currentNode
                        currentSection = None
                        currentSubSection = None

                    else:
                        if currentNode != None:
                            if sectionMatch.match( passage ):
                                lines = passage.split( '\n' )


                                if currentDivision != None:
                                    currentNode = RogetNode( ROGET_NODE_CATEGORY, lines[0], currentDivision )
                                else:
                                    currentNode = RogetNode( ROGET_NODE_CATEGORY, lines[0], currentClass )
                                currentNode._key = lines[1].strip()
                                currentSection = currentNode
                                currentSubSection = None

                            elif subsectionMatch.match( passage ):
                                lines = passage.split( '\n' )
                                currentNode = RogetNode( ROGET_NODE_CATEGORY, None, currentSection )
                                currentSubSection = currentNode
                                currentNode._key = lines[0].strip()
                            else:
                                if passageLines == 1 and not '--' in passage:
                                    if currentSubSection != None:
                                        currentNode = RogetNode( ROGET_NODE_CATEGORY, None, currentSubSection )
                                    else:
                                        currentNode = RogetNode( ROGET_NODE_CATEGORY, None, currentSection )
                                    currentNode._key = passage.strip()
                                else:
                                    self._parseHeadWords( currentNode, passage )
                    passage = ''
                    passageLines = 0

        self._resolveReference( root )

        if self._VERBOSE != 0:
            tm = time.time() - tm
            print("time to parse file: ", tm)

        return RogetThesaurus(root,self._headWordIndex, self._senseIndex)

    def load(self, file ):
        """
        loads an instance of roget thesaurus (if possible from pickled/serialized form)

        if file does not exist
            parse roget thesaursus
            store pickled form to file
        else
            load pickled form from file
        returns instance of RogetThesaurus

        don't use this! surprisingly it takes less time to parse it from the text file.
        (even with this inefficient parser)

        Reason for this seems to be that pickled format is much larger then text file;
        pickle adds the type of the class as first element of sexpression -
        so there is a lot of redundancy and pickled file is much larger than text file.
        """
        res = None
        if os.access( file, os.F_OK | os.R_OK ):
            print('file exists: ', file)
            res = self._loadFromFile( file )

        if res == None:
            print('load from file; current recursion limit ', sys.getrecursionlimit())

            if self._VERBOSE != 0:
                print("Parsing from text: ", file)
                tm = time.time()
            res = self.parse()
            if self._VERBOSE != 0:
                tm = time.time() - tm
                print("time to parse from text: ", tm)
            self._storeToFile( file, res )

        return res

    def _loadFromFile( self, file ):
        try:
            #r = RogetThesaurus()
            if self._VERBOSE != 0:
                print("Load from file: ", file)
                tm = time.time()
            curRecursionLimit = sys.getrecursionlimit()
            if curRecursionLimit < self._RECURSION_LIMIT:
                sys.setrecursionlimit( self._RECURSION_LIMIT )
            with open( file ) as f:
                ret = pickle.load( f )
                if curRecursionLimit < self._RECURSION_LIMIT:
                    sys.setrecursionlimit( curRecursionLimit )
                if self._VERBOSE != 0:
                    tm = time.time() - tm
                print("time to load from file: ", tm)
                return ret
        except Exception as e:
            print('Error while loading thesaurus', e)
            return None

    def _storeToFile( self, file, r ):
        try:
            if self._VERBOSE != 0:
                print("Storing to file: ", file)
                tm = time.time()
            curRecursionLimit = sys.getrecursionlimit()
            if curRecursionLimit < self._RECURSION_LIMIT:
                sys.setrecursionlimit( self._RECURSION_LIMIT )
            print('storing to ' +  file)
            with open( file, 'w') as f:
                pickle.dump( r, f )
            if curRecursionLimit < self._RECURSION_LIMIT:
                sys.setrecursionlimit( curRecursionLimit )
            if self._VERBOSE != 0:
                tm = time.time() - tm
                print("time to store to file: ", tm)
        except Exception as e:
            print('Error while storing thesaurus', e)
            os.remove( file )
            return None


class RogetNode:
    """
        RogetNode - the base class of all nodes maintained by Roget thesaurus
    """
    def __init__(self, typ, description, parent = None):
        global _lastInternalId

        self._type = typ
        if description != None:
            self._description = description.strip()
        else:
            self._description = None
        self._parent = parent
        self._child = []
        self._key = ''
        self._internalId = _lastInternalId
        _lastInternalId += 1
        if parent != None:
            parent._addChild( self )
            #print("addChild ", description, "parent ",parent.description)

    def _addChild(self, nchild):
        self._child.append( nchild )

    def toString(self):
        ret = self.typeToString()
        if self._description != None:
            ret += " - " + self.description
        ret += " ("  + self.key + ")"
        return ret

    def typeToString(self):
        """ returns the type o this node as a string """
        if self._type == ROGET_NODE_CATEGORY:
            return "Category"
        elif self._type == ROGET_NODE_HEADWORD:
            return "Headword"
        elif self._type == ROGET_NODE_SENSE_GROUP:
            return "SenseGroup"
        elif self._type == ROGET_NODE_SENSE:
            return "Sense"

    @property
    def type(self):
        """ returns the type of this node as a integer """
        return self._type

    @property
    def key(self):
        """ the meaning/key of this node """
        return self._key

    @property
    def description(self):
        """ returns an optional description (in the text this appears as [ .... ] ) """
        return self._description

    @property
    def parent(self):
        """ returns the parent node (one up in the ontology) """
        return self._parent

    @property
    def child(self):
        """ returns the array of child nodes """
        return self._child

    @property
    def internalId(self):
        """ each node has its own internal id """
        return self._internalId



class Sense(RogetNode):
    """
        a single sense (the leaf node of the Roget Thesaurus
    """


    #def __init__(self, parent):
    #    self.__init__(self, ROGET_NODE_SENSE, parent)

    def __init__(self, typ, parent):
        RogetNode.__init__( self, typ, None, parent)
        self._comment = ''
        self._link = None
        self._linkComment = None
        self._wordType = WORD_TYPE_NONE

    def toString(self):
        return self._wordToString()

    def _wordToString(self):
        ret = self.typeToString() + " ("  + self.key + ")"
        if self._wordType != WORD_TYPE_NONE:
            ret += ' /'
            if self._wordType ==  WORD_TYPE_ADJ:
                ret += 'Adj'
            if self._wordType ==  WORD_TYPE_VERB:
                ret += 'V'
            if self._wordType ==  WORD_TYPE_ADVERB:
                ret += 'Adv'
            if self._wordType ==  WORD_TYPE_NOUN:
                ret += 'N'
            if self._wordType ==  WORD_TYPE_PHRASE:
                ret += 'Phr'
            ret += '/ '
        if self.comment != '':
            ret += ' comment: ' + self.comment
        if self.link != None:
            ret += " [link: #" + self.link.index
            if self.link.key != None:
                ret += " (" + self.link.key + ")"
            ret += " ]"
        return ret

    @property
    def comment(self):
        """ an optional comment (in the text this is the text that appears in brackets ) """
        return self._comment

    @property
    def link(self):
        """ optional link to a node of type HeadWord (in the text this appears as "&amp;c; 111" - link to headword with id 111 """
        return self._link

    @property
    def linkComment(self):
        """ optional comment on a link """
        return self._linkComment

    @property
    def wordType(self):
        """ optional word type annotation """
        return self._wordType




class HeadWord(Sense):
    """
        A headword
    """
    def __init__(self, HeadIndex, parent):
        Sense.__init__( self, ROGET_NODE_HEADWORD, parent)
        self._index = HeadIndex.strip()

    def toString(self):
        return '#' + self._index  + ' ' + self._wordToString()

    @property
    def index(self):
        """ the string id that identifies the headword in the Roget thesaurus """
        return self._index

class RogetThesaurus:
    """ class Roget
        The Roget Thesaurus class
    """
    #def __init__(self):
    #    self._rootNode = None
    #    self._headWordIndex = None
    #    self._senseIndex = None

    def __init__(self, rootNode = None, headWordIndex = None, senseIndex = None ):
        self._rootNode = rootNode
        self._headWordIndex = headWordIndex
        self._senseIndex = senseIndex

    @property
    def rootNode(self):
        """ the root node of the ontology """
        return self._rootNode

    @property
    def headWordIndex(self):
        """ the index of head words - maps a head word to its node in the ontology """
        return self._headWordIndex

    @property
    def senseIndex(self):
        """ the index of word senses - maps the word sense to a list of nodes in the ontology """
        return self._senseIndex

    # add all parent nodes to array (up to first category); adds the

    def _semHelpAddParents( self, s, ret):
        while s != None:
            ret.append( s )
            if s.type == ROGET_NODE_CATEGORY:
                break
            s = s.parent

    def _semHelpSortedSet( self, word ):
        senses = self.senseIndex
        wordSenses = senses[ word ]
        ret = []
        if wordSenses != None:
            for s in wordSenses:
                self._semHelpAddParents( s, ret )
                if s.link != None:
                    self._semHelpAddParents( s.link, ret )
            ret.sort( key=lambda elm: elm.internalId ) # sort by internal id

        #print("[")
        #for s in ret:
        #    print s.internalId, "," ,
        #print("]")
        return ret

    def semanticSimilarity( self, seq1, seq2 ):
        """ computes the semantic similarity between two terms,

            returns the following tuple (similarity-score, common-node-in-roget-thesaurus)


            the similarity score:
                100 - both terms appear in the same SenseGroup node
                 90 - both terms he the same head word
                 80 - both terms appear in the same leaf category
                  0 - everything else

            common-node-in-roget-thesaurus: is None if the score is 0;
            otherwise it is the common node that the score is based on
        """
        arr1 = self._semHelpSortedSet( seq1 )
        arr2 = self._semHelpSortedSet( seq2 )


        # merging two sorted arrays
        score = 0
        rnode = None

        pos1 = 0
        pos2 = 0
        if arr1 == None or arr2 == None:
            return (0, None)

        while pos1 < len( arr1 ) and pos2 < len( arr2 ):
            if arr1[ pos1 ].internalId == arr2[ pos2 ].internalId:
                node = arr1[ pos1 ]
                if node.type == ROGET_NODE_CATEGORY:
                    nscore = 80
                elif node.type == ROGET_NODE_HEADWORD:
                    nscore = 90
                elif node.type == ROGET_NODE_SENSE_GROUP:
                    nscore = 100

                if score < nscore:
                    score = nscore
                    rnode = node
                    if score == 100:
                        break
                pos1 += 1
                pos2 += 1
            elif arr1[ pos1 ].internalId < arr2[ pos2 ].internalId:
                pos1 += 1
            else:
                pos2 += 1

        return (score, rnode)

class RogetThesaususFormatterText:
    """
        class for formatting of Roget thesaurus as text report
    """
    def show(self, roget, file, mask = 0xF ):
        self._showRogetTextImp( roget.rootNode, 1, file, mask)

    def _showRogetTextImp(self, node, depth, file, mask ):

        if node.type & mask != 0:
            line = ''
            for _ in range(1,depth):
                line += '\t'
            line += node.toString() + '\n'
            file.write( line )

        for n  in node.child:
            self._showRogetTextImp(n , depth + 1, file, mask )

def escapeStr( s ):
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace("\"", "&quot;")
    return s


class RogetThesaurusFormatterXML:
    """
        class for formatting of Roget thesaurus as xml
    """
    def show(self, roget, file):

        file.write( "<?xml version='1.0'?>\n<rogetThesaurus>\n<ontology>" )
        self._showRogetXMLNodes( roget.rootNode, file )
        file.write( "</ontology>" )
        file.write( "</rogetThesaurus>" )

    def _showRogetXMLNodes( self, node, file ):

        txt = "<" + node.typeToString() + " "

        if node.type == ROGET_NODE_CATEGORY:
            txt += 'name="' + escapeStr( node.key ) + '"'
        #elif node.type == ROGET_NODE_SENSE_GROUP:
            # nothing to do
        elif node.type == ROGET_NODE_SENSE or node.type == ROGET_NODE_HEADWORD:
            if node.type == ROGET_NODE_HEADWORD:
                txt += 'id="' + escapeStr( node.index ) + '" '
            txt += 'sense="' + escapeStr( node.key ) + '" '
            if node.wordType != WORD_TYPE_NONE:
                txt += ' wordType="'
                if node.wordType ==  WORD_TYPE_ADJ:
                    txt += 'Adj'
                if node.wordType ==  WORD_TYPE_VERB:
                    txt += 'V'
                if node.wordType ==  WORD_TYPE_ADVERB:
                    txt += 'Adv'
                if node.wordType ==  WORD_TYPE_NOUN:
                    txt += 'N'
                if node.wordType ==  WORD_TYPE_PHRASE:
                    txt += 'Phr'
                txt += '" '
            if node.comment != '':
                txt += ' comment="' + escapeStr( node.comment ) + '" '
            if node.link != None:
                txt += ' link="' + escapeStr( node.link.index ) + '" '
                if node.link.key != None:
                    txt  += ' linkComment="' + escapeStr( node.link.key )+ '" '
        txt += ">"
        file.write( txt + '\n' )

        for n  in node.child:
            self._showRogetXMLNodes( n, file )
            file.write( " " )

        file.write( "</" + node.typeToString() + ">" )



