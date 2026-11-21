"""ENEM 2024 D2 C5 p020 Q147-Q148 with single-column integration and PDF provenance."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import json,hashlib,argparse,pymupdf
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
a=argparse.ArgumentParser();a.add_argument("--pdf",type=Path,required=True);args=a.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p020_layout.json").read_text(encoding="utf8"))
assert [v["number"] for v in layout["questions"]]==[147,148]
assert layout["layout"]["mode"]=="single_column" and layout["layout"]["columns"][0]["order"]==[147,148]
assert layout["source"]["printed_page"]==20 and layout["source"]["pdf_page_index"]==19
assert len(layout["media"])==6 and len(layout["response_targets"])==10
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
d=pymupdf.open(str(args.pdf));page=d[19];assert len(d)==32
words=page.get_text("words")
for t in layout["response_targets"]:
 assert len([w for w in words if w[4]==t["label"] and abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08])==1,t
for key,m in layout["media"].items():
 file=root/m["url"]
 assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==m["sha256"],key
 if m["source_kind"]=="native_image":
  assert m["source_xref"]==210
  assert hashlib.sha256(d.extract_image(210)["image"]).hexdigest()==m["sha256"]
 else:
  png=page.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(m["source_bbox"]),alpha=False).tobytes("png")
  assert hashlib.sha256(png).hexdigest()==m["sha256"],key
q147=json.loads((root/layout["questions"][0]["source_data"]).read_text(encoding="utf8"))
q148=json.loads((root/layout["questions"][1]["source_data"]).read_text(encoding="utf8"))
assert [v["label"] for v in q147["options"]]==list("ABCDE")
assert all(v["image_only"] and v["asset"]==layout["media"]["q147-"+v["label"]]["url"] for v in q147["options"])
assert [v["label"] for v in q148["options"]]==list("ABCDE")
assert [v["text"] for v in q148["options"]]==["I","II","III","IV","V"]
assert all("gabarito" not in str(v).lower() for v in (q147["options"],q148["options"]))
print("SOURCE_PASS 10_NATIVE_LABELS 5_PDF_MATH_CROPS 1_NATIVE_SCHEME",flush=True)
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def ck(name,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",name,flush=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   context=browser.new_context(viewport={"width":width,"height":844})
   pg=context.new_page();errors=[]
   pg.on("pageerror",lambda e:errors.append(str(e)))
   res=pg.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=20&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   ck(mode+"_status",res.status==200)
   ck(mode+"_two_questions",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 147","QUESTÃO 148"])
   ck(mode+"_one_fullwidth_column",pg.locator(".page-columns.single-column .page-column").count()==1)
   ck(mode+"_ten_radio_options",pg.locator(".page-question input[type=radio]").count()==10)
   ck(mode+"_five_formula_imgs",pg.locator(".page-question").nth(0).locator(".page-q-option img").count()==5)
   ck(mode+"_one_cameras_img",pg.locator(".page-question").nth(1).locator("figure img").count()==1)
   ck(mode+"_six_media_loaded",pg.locator(".page-question img").evaluate_all("(xs)=>xs.length===6&&xs.every(im=>im.complete&&im.naturalWidth>0)"))
   ck(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile" and pg.locator("#page-reading-mode").count():
    ck("mobile_read_mode_on",pg.locator("#page-viewport.read-mode").count()==1)
    ck("mobile_single_column",pg.locator(".page-column").count()==1)
   for i,value in ((0,"B"),(1,"D")):pg.locator(".page-question").nth(i).locator(f"input[value={value}]").check()
   pg.reload(wait_until="networkidle")
   ck(mode+"_independent_drafts",pg.locator(".page-question").nth(0).locator("input[value=B]").is_checked() and pg.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
   ck(mode+"_no_js_errors",not errors)
   image=root/f"p020_renderer_{mode}.png"
   pg.screenshot(path=str(image),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(image.read_bytes()).hexdigest(),flush=True)
   context.close()
  browser.close()
finally:srv.shutdown()
ck("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
