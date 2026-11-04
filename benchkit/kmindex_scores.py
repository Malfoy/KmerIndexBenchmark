import json,gzip
from pathlib import Path
def open_output(path):
    return path.open() if path.exists() else gzip.open(str(path)+".gz","rt")

def stream_scores(path, chunk_size=65536):
    """Stream the nested kmindex JSON object with bounded per-query memory."""
    decoder=json.JSONDecoder()
    with open_output(path) as f:
        buf="";pos=0;eof=False
        def fill():
            nonlocal buf,pos,eof
            buf=buf[pos:];pos=0
            chunk=f.read(chunk_size);buf+=chunk;eof=not chunk
        def peek():
            nonlocal pos
            while True:
                while pos<len(buf) and buf[pos].isspace():pos+=1
                if pos<len(buf):return buf[pos]
                if eof:raise ValueError("Unexpected end of JSON")
                fill()
        def take(char):
            nonlocal pos
            if peek()!=char:raise ValueError(f"Expected {char} in JSON")
            pos+=1
        def value():
            nonlocal pos
            peek()
            while True:
                try:
                    result,end=decoder.raw_decode(buf,pos);pos=end;return result
                except json.JSONDecodeError:
                    if eof:raise
                    fill()
        take("{")
        if value()!="atb":raise ValueError("Unexpected kmindex index name")
        take(":");take("{")
        if peek()!="}":
            while True:
                qid=value();take(":");scores=value()
                yield qid,scores
                if peek()=="}":break
                take(",")
        take("}");take("}")
        if (buf[pos:]+f.read()).strip():raise ValueError("Trailing JSON data")
