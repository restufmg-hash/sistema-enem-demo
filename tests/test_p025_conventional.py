"""ENEM 2024 Dia 2 C5 p025 Q157-Q160: provenance and browser validation."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import argparse,hashlib,json,pymupdf
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--pdf",type=Path,required=True);args=parser.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p025_layout.json").read_text(encoding="utf8"))
assert [q["number"] for q in layout["questions"]]==[157,158,159,160]
assert layout["layout"]["mode"]=="two_column"
assert [c["order"] for c in layout["layout"]["columns"]]==[[157,158],[159,160]]
assert layout["source"]["printed_page"]==25 and layout["source"]["pdf_page_index"]==24
assert len(layout["media"])==6 and len(layout["response_targets"])==20
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
doc=pymupdf.open(str(args.pdf));assert len(doc)==32
page=doc[24];words=page.get_text("words")
for target in layout["response_targets"]:
 matches=[w for w in words if w[4]==target["label"] and abs(w[0]-target["bbox"][0])<0.08 and abs(w[1]-target["bbox"][1])<0.08]
 assert len(matches)==1,(target,matches)
for key,item in layout["media"].items():
 f=root/item["url"];assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==item["sha256"],key
 if item["source_kind"]=="native_image":
  assert item["source_xref"]==272
  assert hashlib.sha256(doc.extract_image(272)["image"]).hexdigest()==item["sha256"]
  assert len(page.get_image_rects(272))==1
 else:
  blob=page.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(item["source_bbox"]),alpha=False).tobytes("png")
  assert hashlib.sha256(blob).hexdigest()==item["sha256"],key
qs=[json.loads((root/q["source_data"]).read_text(encoding="utf8")) for q in layout["questions"]]
assert [q["number"] for q in qs]==[157,158,159,160]
assert all([o["label"] for o in q["options"]]==list("ABCDE") for q in qs)
assert all(not any(k in q for k in ("correct_answer","correct_option","gabarito")) for q in qs)
assert all(o["image_only"] and o["asset"]==layout["media"]["q158-"+o["label"]]["url"] for o in qs[1]["options"])
assert [o["text"] for o in qs[0]["options"]]==["8 250.","7 920.","6 545.","5 500.","5 280."]
assert [o["text"] for o in qs[2]["options"]]==["147,00.","150,00.","162,50.","165,75.","168,00."]
assert [o["text"] for o in qs[3]["options"]]==["12,50","20,00","24,00","30,00","37,50"]
assert sum(b["type"]=="image" for b in qs[2]["blocks"])==1
print("SOURCE_PASS PDF_SHA 20_ALTERNATIVE_POSITIONS 5_VECTOR_FORMULAS 1_NATIVE_PROMOTION",flush=True)
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def ck(name,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",name,flush=True)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   ctx=b.new_context(viewport={"width":width,"height":844})
   p=ctx.new_page();errs=[];p.on("pageerror",lambda err:errs.append(str(err)))
   resp=p.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=25&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   ck(mode+"_http200",resp.status==200)
   ck(mode+"_all_four",p.locator(".page-question h2").all_inner_texts()==[f"QUESTÃO {n}" for n in (157,158,159,160)])
   ck(mode+"_two_source_columns",p.locator(".page-columns .page-column").count()==2)
   ck(mode+"_20_radio_options",p.locator(".page-question input[type=radio]").count()==20)
   ck(mode+"_five_formula_images",p.locator(".page-question").nth(1).locator(".page-q-option.visual img").count()==5)
   ck(mode+"_promotion_image",p.locator(".page-question").nth(2).locator("figure img").count()==1)
   ck(mode+"_six_media_loaded",p.locator(".page-question img").evaluate_all("(xs)=>xs.length===6&&xs.every(x=>x.complete&&x.naturalWidth>0)"))
   ck(mode+"_no_external_overflow",p.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile":
    ck("mobile_read_mode",p.locator("#page-viewport.read-mode").count()==1)
    ck("mobile_formula_fits",p.locator(".page-question").nth(1).locator(".page-q-option.visual img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>{let a=x.getBoundingClientRect(),b=x.closest('label').getBoundingClientRect();return a.right<=b.right+1&&a.width>40;})"))
   for idx,label in enumerate("ABCD"):p.locator(".page-question").nth(idx).locator(f"input[value={label}]").check()
   p.reload(wait_until="networkidle")
   ck(mode+"_four_drafts_restored",all(p.locator(".page-question").nth(i).locator(f"input[value={letter}]").is_checked() for i,letter in enumerate("ABCD")))
   ck(mode+"_no_js_errors",not errs)
   screenshot=root/f"p025_renderer_{mode}.png"
   p.screenshot(path=str(screenshot),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(screenshot.read_bytes()).hexdigest(),flush=True)
   ctx.close()
  b.close()
finally:srv.shutdown()
ck("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
