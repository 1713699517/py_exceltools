#! python
# -*- coding:utf-8 -*-

import os
import sys
import json
from datetime import datetime

from error import raise_ex
from error import RowError
from error import SheetError
from error import ColumnError

try:
    basestring
except NameError:
    basestring = str

try:
    long
except NameError:
    long = int

class Writer:

    def __init__(self,doc_name,sheet_name,row_offset,col_offset):
        self.doc_name   = doc_name
        self.sheet_name = sheet_name
        self.row_offset = row_offset
        self.col_offset = col_offset

    def suffix(self):
        return ".json"

    def to_json_value(self,value_type,value):
        if "int" == value_type :
            return int( value )
        elif "int64" == value_type :
            return long( value )
        elif "number" == value_type :
            # 去除带小数时的小数点，100.0 ==>> 100
            if long( value ) == float( value ) :
                return long( value )
            return float( value )
        elif "string" == value_type :
            return value
        elif "json" == value_type :
            return json.loads( value )
        else :
            raise Exception( "invalid type",value_type )

    def column_ctx(self,values):
        key = None

        # key可能为空
        if None != self.types[0] and None != values[0] : key = str( values[0] )

        ctx = {}
        for index in range( 1,len( values ) ):
            try:
                # 允许某个字段为空，因为并不是所有行都需要这些字段
                if None != self.fields[index] and None != values[index] :
                    key = str( self.fields[index] )
                    val = self.to_json_value( self.types[index],values[index] )
                    
                    ctx[key] = val
            except Exception as e:
                raise_ex( ColumnError( index + 1,e ),sys.exc_info()[2] )

        return key, ctx

    def is_object(self):
        for column_values in self.rows:
            if None != column_values[0] : return True

        return False

    def object_ctx(self):
        content = {}
        for row_index,column_values in enumerate( self.rows ) :
            try:
                key,json_val = self.column_ctx( column_values )
                if None == key : key = str( row_index )

                content[key] = json_val
            except ColumnError as e:
                raise_ex( RowError( 
                    str(e),row_index + 1 + self.row_offset),sys.exc_info()[2] )

        return content

    def array_ctx(self):
        content = []
        for row_index,column_values in enumerate( self.rows ) :
            try:
                key,json_val = self.column_ctx( column_values )

                content.append( json_val )
            except ColumnError as e:
                raise_ex( RowError( 
                    str(e),row_index + 1 + self.row_offset),sys.exc_info()[2] )

        return content

    def object_content(self,types,fields,rows):
        try:
            self.types  = types
            self.fields = fields
            self.rows   = rows

            ctx = {}
            for row_index,value in enumerate( self.rows ) :
                key = self.fields[row_index]
                if None != key :
                    value_type = self.types[row_index]
                    ctx[key] = self.to_json_value( value_type,value )

            return json.dumps( ctx,ensure_ascii=False,indent=4 )
        except RowError as e:
            raise_ex( SheetError( str(e),self.sheet_name ),sys.exc_info()[2] )

    def array_content(self,types,fields,rows):
        try:
            self.types  = types
            self.fields = fields
            self.rows   = rows
            ctx = None
            if self.is_object() :
                ctx = self.object_ctx()
            else :
                ctx = self.array_ctx()

            return json.dumps( ctx,ensure_ascii=False,indent=4,sort_keys=True )
        except RowError as e:
            raise_ex( SheetError( str(e),self.sheet_name ),sys.exc_info()[2] )