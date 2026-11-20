"""Source/media test: Python tests/test_p012_source_integrity.py --pdf 2024_PV_impresso_D2_CD5.pdf."""
from pathlib import Path
import argparse,hashlib,json
import pymupdf
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--pdf",type=Path,required=True)
pdf=parser.parse_args().pdf
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p012_layout.json").read_text(encoding="utf-8"))
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
doc=pymupdf.open(str(pdf))
assert len(doc)==32 and layout["source"]["pdf_page_index"]==11 and layout["source"]["printed_page"]==12
page=doc[11]
assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<0.01
assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<0.01
assert [x["number"] for x in layout["questions"]]==[122,123]
assert len(layout["response_targets"])==10
assert layout["layout"]["columns"][0]["order"]==[122]
assert layout["layout"]["columns"][1]["order"]==[122,123]
q122=layout["questions"][0]
assert q122["continuation_column"]=="right"
assert len(q122["asset_splices"])==2
assert q122["continuation_start_char"]>q122["asset_splices"][-1]["end_char"]
native_words=page.get_text("words")
found=[]
for target in layout["response_targets"]:
 label=target["label"]
 matches=[w for w in native_words if w[4]==label and abs(w[0]-target["bbox"][0])<0.06 and abs(w[1]-target["bbox"][1])<0.06]
 assert len(matches)==1,(label,target)
 found.append((target["question_id"],label))
assert len(set(found))==10
for key,media in layout["media"].items():
 f=root/media["url"]
 assert hashlib.sha256(f.read_bytes()).hexdigest()==media["sha256"],key
 assert media["source_pdf_page"]==12
 bbox=media["source_bbox"]
 rendered=page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(*bbox),alpha=False)
 assert hashlib.sha256(rendered.tobytes("png")).hexdigest()==media["sha256"],key
 print("PASS_MEDIA",key,media["sha256"])
print("PASS SOURCE SHA, PAGE BBOX, CROSS-COLUMN, TEN ANSWER TARGETS, THREE PDF-NATIVE FIGURES")
