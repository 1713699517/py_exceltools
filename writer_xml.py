#! python
# -*- coding:utf-8 -*-

import os
import sys
import json
from datetime import datetime
from xml.dom.minidom import Document

from error import raise_ex
from error import RowError
from error import SheetError
from error import ColumnError

try:
    basestring
except NameError:
    basestring = str

class Writer:

    def __init__(self,types,fields,rows):
        self.types  = types
        self.fields = fields
        self.rows   = rows
        self.doc    = Document()  #创建DOM文档对象

    def suffix(self):
        return ".xml"

    def comment(self):
        now = datetime.now()
        comment = '<!--\n'
        comment += 'DO NOT MODITY!  Auto generated by py_exceltools\n'
        comment += 'https://www.python.org/\n'
        comment += 'http://www.python-excel.org/\n\n'
        comment += 'At ' + now.strftime('%Y-%m-%d %H:%M:%S') + '\n\n'

        comment += '-->\n\n'
        return comment

    def json_to_xml(self,node,json_val):
        if isinstance( json_val,dict ) :
            for k,v in json_val.items() :
                sub_node = self.doc.createElement( k )
                self.json_to_xml( sub_node,v )
                node.appendChild( sub_node )
        elif isinstance( json_val,list ) :
            for k,v in enumerate( json_val ) :
                # xml中并不支持array，用item来命名，外加一个index属性
                sub_node = self.doc.createElement( "item" )
                sub_node.setAttribute( "index",str( k ) )
                self.json_to_xml( sub_node,v )
                node.appendChild( sub_node )
        elif isinstance( json_val,int ): 
            self.to_xml_value( node,"int64",json_val )
        elif isinstance( json_val,basestring ):
            self.to_xml_value( node,"string",json_val )
        elif isinstance( json_val,float ):
            self.to_xml_value( node,"number",json_val )
        else:
            raise Exception( "unknow json type",json_val )

    def to_xml_value(self,node,value_type,value):
        sub_node = None
        if "int" == value_type :
            sub_node = self.doc.createTextNode( str( int( value ) ) )
        elif "int64" == value_type :
            sub_node = self.doc.createTextNode( str( long( value ) ) )
        elif "number" == value_type :
            # 去除带小数时的小数点，100.0 ==>> 100
            if long( value ) == float( value ) :
                sub_node = self.doc.createTextNode( str( long( value ) ) )
            sub_node = self.doc.createTextNode( str( float( value ) ) )
        elif "string" == value_type :
            sub_node = self.doc.createTextNode( value )
        elif "json" == value_type :
            self.json_to_xml( node,json.loads( value ) )
            return
        else :
            raise Exception( "invalid type",value_type )

        node.setAttribute( "type",value_type )
        node.appendChild( sub_node )

    def column_ctx(self,sheet_name,values):
        node = self.doc.createElement( sheet_name )

        # key可能为空
        if None != self.types[0] and None != values[0] :
            node.setAttribute( "key",str( values[0] ) )

        for index in range( 1,len( values ) ):
            try:
                # 允许某个字段为空，因为并不是所有行都需要这些字段
                if self.fields[index] and values[index] :
                    sub_node = self.doc.createElement( str( self.fields[index] ) )
                    val = self.to_xml_value( 
                        sub_node,self.types[index],values[index] )

                    node.appendChild( sub_node )
            except Exception as e:
                raise_ex( ColumnError( index + 1,e ),sys.exc_info()[2] )

        return node

    def row_ctx(self,doc_name,sheet_name,CLT_ROW):
        root = self.doc.createElement( doc_name + "_" + sheet_name ) #创建根元素
        for row_index,column_values in enumerate( self.rows ) :
            try:
                node = self.column_ctx( sheet_name,column_values )
                root.appendChild( node )
            except ColumnError as e:
                raise_ex( RowError( 
                    str(e),row_index + 1 + CLT_ROW),sys.exc_info()[2] )

        return root

    def content(self,doc_name,sheet_name,CLT_ROW):
        try:
            root = self.row_ctx( doc_name,sheet_name,CLT_ROW )
            self.doc.appendChild( root )

            return self.comment() + self.doc.toprettyxml( indent="   " )
        except RowError as e:
            raise_ex( SheetError( str(e),sheet_name ),sys.exc_info()[2] )