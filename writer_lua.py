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

# 在python中，字符串和unicode是不一样的。默认从excel读取的数据都是unicode。
# str可以通过decode转换为unicode
# ascii' codec can't encode characters
def to_unicode_str( val ):
    if isinstance( val,str ) :
        return val
    elif isinstance( val,unicode ) :
        return val
    else :
        return str( val ).decode("utf8")

BASE_LENGTH = 120
BASE_INDENT = "    "

class Writer:

    def __init__(self,doc_name,sheet_name,row_offset,col_offset):
        self.doc_name   = doc_name
        self.sheet_name = sheet_name
        self.row_offset = row_offset
        self.col_offset = col_offset

        self.indent = {}

    def suffix(self):
        return ".lua"

    def indent_ctx( self,indent ):
        if indent <= 0: return ""

        if indent not in self.indent:
            ctx = BASE_INDENT*indent
            self.indent[indent] = ctx

        return self.indent[indent]

    def comment(self):
        now = datetime.now()
        comment = '--[[\n'
        comment += 'DO NOT MODITY!  Auto generated by py_exceltools\n'
        comment += 'https://www.python.org/\n'
        comment += 'http://www.python-excel.org/\n'
        comment += ']]\n\n'
        comment += '-- At ' + now.strftime('%Y-%m-%d %H:%M:%S') + '\n\n'
        return comment

    def json_ctx(self,json_val,indent):
        ctx = ""
        indent_str = self.indent_ctx( indent )
        next_indent_str = self.indent_ctx( indent + 1 )
        if isinstance( json_val,dict ):
            for k,v in json_val.items():
                key = None
                new_line,val = self.json_ctx( v,indent + 1 )
                if new_line :
                    key = next_indent_str + "['" + str( k ) + "'] =\n"
                else:
                    key = next_indent_str + "['" + str( k ) + "'] = "
                ctx = key + val + ",\n"
            return True,indent_str + "{\n" + ctx + indent_str + "}"
        elif isinstance( json_val,list ):
            val_list = []
            # 暂时不缩进，因为不知道是否要换行
            for v in json_val:
                new_line,val_str = self.json_ctx( v,0 )
                val_list.append( val_str + "," )

            # 如果内容太少，可以不换行
            length = 0
            multi_line = False
            for val in val_list:
                curr_len = len( val )
                if length + curr_len > BASE_LENGTH:
                    ctx += "\n" + next_indent_str
                    length = 0
                    multi_line = True
                ctx += val
                length += curr_len
            
            if multi_line or len( ctx ) > BASE_LENGTH :
                return True,indent_str + "{\n" + \
                    next_indent_str + ctx + indent_str + "\n}"
            else:
                return False,"{" + ctx + "}"

        elif isinstance( json_val,int ): 
            return False,indent_str + str( long( json_val ) )
        elif isinstance( json_val,basestring ):
            return False,indent_str + "'" + json_val + "'"
        elif isinstance( json_val,float ):
            if long( json_val ) == json_val:
                return False,indent_str + str( long( json_val ) )
            return False,indent_str + str( json_val )
        else:
            raise Exception( "unknow json type",json_val )

    def value_to_str(self,value_type,value,indent):
        if "int" == value_type :
            return False,str( int( value ) )
        elif "int64" == value_type :
            # 两次转换保证为数字
            return False,str( long( value ) )
        elif "number" == value_type :
            # 去除带小数时的小数点，100.0 ==>> 100
            if long( value ) == float( value ) :
                return False,str( long( value ) )
            return False,str( float( value ) )
        elif "string" == value_type :
            return False,"'" + to_unicode_str( value ) + "'"
        elif "json" == value_type :
            new_line,val_str = self.json_ctx( json.loads( value ),indent )
            if new_line :
                return new_line,"\n" + val_str
            else :
                return new_line,val_str
        else :
            raise Exception( "invalid type",value_type )

    def pair_to_str(self,field_name,value_type,value,indent):
        key_str = "['" + field_name + "'] ="
        new_line,val_str = self.value_to_str( value_type,value,indent )
        if not new_line : key_str += " "

        indent_str = self.indent_ctx( indent )
        return indent_str + key_str + val_str + ",\n"

    def column_ctx(self,values,indent):
        key = ""

        try:
            if None != self.types[0] and None != values[0] : # key可能为空
                indent_str = self.indent_ctx( indent - 1 )
                key = indent_str + "[" + \
                    self.value_to_str( self.types[0],values[0],indent ) + "] =\n"
        except:
            raise_ex( ColumnError( 0 + 1 ),sys.exc_info()[2] )

        ctx = ""
        for index in range( 1,len( values ) ):
            try:
                # 允许某个字段为空，因为并不是所有行都需要这些字段
                if None != self.fields[index] and None != values[index] :
                    ctx += self.pair_to_str( self.fields[index],
                        self.types[index],values[index],indent )
            except Exception as e:
                raise_ex( ColumnError( index + 1,e ),sys.exc_info()[2] )

        return key, ctx

    def row_ctx(self):
        ctx = ""
        indent_str = self.indent_ctx( 1 )
        for row_index,column_values in enumerate( self.rows ) :
            try:
                key,col_ctx = self.column_ctx( column_values,2 )
                ctx += indent_str + key + "{\n" + col_ctx + indent_str + "},\n"
            except ColumnError as e:
                raise_ex( RowError( 
                    str(e),row_index + 1 + self.row_offset),sys.exc_info()[2] )

        return ctx

    def array_content(self,types,fields,rows):
        try:
            self.types  = types
            self.fields = fields
            self.rows   = rows
            row_ctx = self.row_ctx()
            ctx = self.comment() + "return\n{\n" + row_ctx + "}"
            return ctx
        except RowError as e:
            raise_ex( SheetError( str(e),self.sheet_name ),sys.exc_info()[2] )

    def object_content(self,types,fields,rows):
        try:
            self.types  = types
            self.fields = fields
            self.rows   = rows

            row_ctx = ""
            for row_index,value in enumerate( self.rows ) :
                key = self.fields[row_index]
                if None != key :
                    value_type = self.types[row_index]
                    row_ctx += self.pair_to_str( key,value_type,value,1 )

            ctx = self.comment() + "return\n{\n" + row_ctx + "}"
            return ctx
        except RowError as e:
            raise_ex( SheetError( str(e),self.sheet_name ),sys.exc_info()[2] )