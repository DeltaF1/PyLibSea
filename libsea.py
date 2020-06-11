# Copyright 2019 Aldous Rice-Leech
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import collections
import re
from collections import *
import itertools

def _indent(string, amount):
    if amount == 0: return string
    lines = string.split('\n')
    for i, line in enumerate(lines):
        # This is a check for new line case. Kinda hacky: FIXME
        if line:
            lines[i] = amount * " " + line
    return '\n'.join(lines)

def indentable(func):
    def wrapper(*args, **kwargs):
        indent = kwargs.pop('indent', 0)
        result = func(*args, **kwargs)
        return _indent(result, indent)
    return wrapper

class Element:
    """
    A base class for describing LibSea types.
    """
    TERM = ";"
    
    def _label(self, name, labels=False):
        if labels:
            return "@"+name+"="
        else:
            return ""
    def __str__(self):
        return self.serialize(labels=True)
        
    @indentable
    def serialize(self, labels=False):
        """
        The following standards are defined for any classes implementing serialize

        1. The method must accept a "labels" keyword argument
        2. The method must accept an "indent" keyword argument, or 
           be wrapped by the @indentable decorator
        3. The method should respect the indent value passed in and apply it to all
           output lines, or be wrapped by the @indentable decorator
        4. The method should indent internally where appropriate
        5. The return value should not end in a ';' separator, or in a newline
        """
        return ""
       
def ser(obj, *args, **kwargs):
    if type(obj) == str:
        obj = String(obj)
    elif type(obj) == float:
        obj = Double(obj)
    elif type(obj) == int:
        obj = Integer(obj)
    elif type(obj) == list:
        obj = List(obj)
    elif isinstance(obj, collections.Mapping):
        obj = Object(obj)
    elif isinstance(obj, tuple):
        try:
            fields = obj._fields
        except AttributeError:
            fields = ()
        obj = Tuple(fields, obj)
    elif obj == None:
        obj = ""
        
    try:
        string = obj.serialize(*args, **kwargs)
    except AttributeError:
        string = str(obj)
        
    return string
        
def to_libsea_string(obj):
    t = type(obj)
    if t == str:
        obj = '"' + str(obj) + '"'
    else:
        obj = str(obj)

class Value(Element):
    def __init__(self, value=None):
        self.value = value

    @indentable
    def serialize(self, labels=False):
        """
        Write out the python string representation of this object
        """
        return str(self.value)        
class String(Value):
    def __init__(self, value):
        self.value = value.replace('\r', r'\r').replace('\n', r'\n')
    @indentable
    def serialize(self, labels=False):
        return '"' + re.sub(r'([\\"\n\r\t\f\b|])', r'\\\1', str(self.value)) + '"'

class Bool(Value):
    @indentable
    def serialize(self, labels=False):
        if self.value:
            return 'T'
        else:
            return 'F'

class Identifier(Value):
    @indentable
    def serialize(self, labels=False):
        return '$'+str(self.value)

class Double(Value):
    pass

class Integer(Value):
    pass

class Tuple(Element):
    def __init__(self, names, values):
        self.names = names
        self.values = values
        
    @indentable
    def serialize(self, labels=True):
        if self.names:
           return "{" + ' '.join(self._label(name, labels=labels)+ser(value, labels=labels)+self.TERM for name,value in zip(self.names, self.values)) + "}"
        else:
            return "{" + ' '.join(ser(value, labels=labels)+self.TERM for value in self.values) + "}" 

Link = namedtuple('Link', ('source','destination'))
attrValue = namedtuple('attrValue', ('id', 'value'))

class List(Element):
    def __init__(self, items):
        self.items = items

    @indentable
    def serialize(self, labels=False):
        output = "[\n"
        output += ",\n".join(ser(item, indent=4, labels=labels) for item in self.items)
        output += "\n]"
        
        return output

class Object(Element):
    def __init__(self, dict):
        self.dict = dict
        
    @indentable
    def serialize(self, labels=True):
        output = "{\n"
        for key, value in self.dict.items():
            output += _indent(self._label(key, labels=labels)+ser(value, labels=labels)+self.TERM+"\n", 4)
            
        output += "}"
        
        return output

def attributeDefinition():
    return OrderedDict(
        name=None,
        type=None,
        default=None,
        nodeValues=[],
        linkValues=[],
        pathValues=[],
    )
    
def enumeration():
    return OrderedDict(
        name=None,
        enumerators=[],
    )
    
def qualifier():
    return OrderedDict(
        type=None,
        name=None,
        description=None,
        attributes=[],
    )

class Graph(Element):
    def __init__(self, name="Graph"):
        self.name = name
        self.nodes = []
        self.links = []
        self.paths = []
        
        self.enums = []
        self.attributes = []
        self.attribute_order = {}
        self.qualifiers = []
        
    @indentable
    def print_var(self, name, value, labels=True):
        return self._label(name, labels=labels)+ser(value, labels=labels)+self.TERM+"\n"
        
    @indentable
    def serialize(self, labels=True, comments=True):
        
        output = "Graph\n"
        output += "{\n"

        if comments: output += _indent("# Metadata\n", 4)
        output += self.print_var('name', self.name, indent=4, labels=labels)
        output += self.print_var('description', self.description, indent=4, labels=labels)
        if comments: output += "\n"
        
        if comments: output += _indent("# Lengths\n", 4)
        output += self.print_var('numNodes', len(self.nodes), indent=4, labels=labels)
        output += self.print_var('numLinks', len(self.links), indent=4, labels=labels)
        output += self.print_var('numPaths', len(self.paths), indent=4, labels=labels)
        output += self.print_var('numPathLinks', 0, indent=4, labels=labels) #FIXME
        if comments: output += "\n"
        
        if comments: output += _indent("# Structural information\n", 4)
        output += self.print_var('links', self.links, indent=4, labels=labels)
        output += self.print_var('paths', self.paths, indent=4, labels=labels)
        if comments: output += "\n"
        
        if comments: output += _indent("# Attributes\n", 4)
        output += self.print_var('enumerations', self.enums, indent=4, labels=labels)
        output += self.print_var('attributeDefinitions', self.attributes, indent=4, labels=labels)
        output += self.print_var('qualifiers', self.qualifiers, indent=4, labels=labels)
        if comments: output += "\n"
        
        if comments: output += _indent("# Visualization\n", 4)
        output += self.print_var('filters', None, indent=4, labels=labels)
        output += self.print_var('selectors', None, indent=4, labels=labels)
        output += self.print_var('displays', None, indent=4, labels=labels)
        output += self.print_var('presentations', None, indent=4, labels=labels)
        if comments: output += "\n"
        
        if comments: output += _indent("# Interface\n", 4)
        output += self.print_var('presentationMenus', None, indent=4, labels=labels)
        output += self.print_var('displayMenus', None, indent=4, labels=labels)
        output += self.print_var('selectorMenus', None, indent=4, labels=labels)
        output += self.print_var('filterMenus', None, indent=4, labels=labels)
        output += self.print_var('attributeMenus', None, indent=4, labels=labels)
        
        output += "}"
        
        return output
        
    def from_graph(graph):

        LibSea = Graph()
        
        LibSea.name = graph.graph_attr.get('name', 'Graph')
        LibSea.description = graph.graph_attr.get('description', 'Generated by libsea.py')

        attributes = defaultdict(lambda: defaultdict(dict))
        
        # Lookup table to get libsea node id from graphviz node
        node_order = {}
        for i, node in enumerate(graph.nodes()):
            node_order[node] = i
            
            # For every attribute that this node has
            for attribute_name in node.attr:
                value = node.attr[attribute_name]
                if value == "True": value = Value('T')
                elif value == "False": value = Value('F')
                # Add it to the appropriate atrtibute definition as a key-value store of id : value
                attributes[attribute_name]['nodeValues'][i] = value
                # This will be converted to {@id=i; @value=node.attr[attribute_name]}
            
        if len(node_order) != len(graph.nodes()):
            raise Exception("Node collision")
        
        # replace with links = List()
        links = []
        for i, edge in enumerate(graph.edges()):
            id1 = node_order[edge[0]]
            id2 = node_order[edge[1]]
            
            links.append(Link(id1, id2))

            for attribute_name in edge.attr:
                value = edge.attr[attribute_name]
                if value == "True": value = Value('T')
                elif value == "False": value = Value('F')
                attributes[attribute_name]['linkValues'][i] = value

        LibSea.nodes = node_order
        LibSea.links = links

        
        for i, name in enumerate(attributes):
            data = attributes[name]
            
            attr = attributeDefinition()
            
            attr['name'] = Identifier(name)
            # FIXME: root and tree_link need to be bool, not string
            attr['type'] = Value('string')
            attr['nodeValues'] = [attrValue(id, value) for id, value in data['nodeValues'].items()]
            attr['linkValues'] = [attrValue(id, value) for id, value in data['linkValues'].items()]
            
            LibSea.attributes.append(attr)
            LibSea.attribute_order[name] = i
            
        LibSea.attributes[LibSea.attribute_order['root']]['type'] = Value('bool')
        LibSea.attributes[LibSea.attribute_order['tree_link']]['type'] = Value('bool')
            
        LibSea.qualifiers.append(OrderedDict(
            type=Identifier("spanning_tree"),
            name=Identifier("default_spanning_tree"),
            description="Spanning tree for walrus",
            attributes=[
                (LibSea.attribute_order['root'], Identifier('root')),
                (LibSea.attribute_order['tree_link'], Identifier('tree_link')),
            ]
        ))
            
        return LibSea
        
    def add_tree(self, tree):
        pass
