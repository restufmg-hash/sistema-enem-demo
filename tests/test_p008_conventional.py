"""Auditoria do PDF convencional opcional e smoke Chromium da página 8.
python tests/test_p008_conventional.py [--pdf CAMINHO_DO_PDF]
"""
from pathlib import Path
from threading import Thread
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import argparse,hashlib,json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument("--pdf",type=Path)
args=parser.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p008_layout.json").read_text(encoding="utf-8"))
assert layout["source"]["printed_page"]==8 and layout["source"]["pdf_page_index"]==7
assert [q["number"] for q in layout["questions"]]==[109,110,111]
assert len(layout["response_targets"])==15
assert len(layout["media"])==7
for key,media in layout["media"].items():
 path=root/media["url"]
 assert path.is_file()
 assert hashlib.sha256(path.read_bytes()).hexdigest()==media["sha256"],key
 assert media["source_pdf_page"]==8
if args.pdf is not None:
 import pymupdf
 assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
 doc=pymupdf.open(str(args.pdf))
 assert len(doc)==32
 page=doc[7]
 assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<.01
 assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<.01
 words=page.get_text("words")
 for target in layout["response_targets"]:
  matches=[w for w in words if w[4]==target["label"] and
   abs(w[0]-target["bbox"][0])<.07 and abs(w[1]-target["bbox"][1])<.07]
  assert len(matches)==1,(target,matches)
 for key,media in layout["media"].items():
  xrefs=[xref for xref,*_ in page.get_images(full=True) if
   any(abs(r.x0-media["source_bbox"][0])<.05 and abs(r.y0-media["source_bbox"][1])<.05 for r in page.get_image_rects(xref))]
  assert len(xrefs)==1,(key,xrefs)
  native=doc.extract_image(xrefs[0])["image"]
  assert hashlib.sha256(native).hexdigest()==media["sha256"]
 print("SOURCE_PASS PDF_SHA, 15_LABELS, SEVEN_NATIVE_MEDIA")
else:
 print("SOURCE_PDF_NOT_CHECKED: use --pdf for independent source verification")
class Handler(SimpleHTTPRequestHandler):
 posts=0
 def do_POST(self):
  Handler.posts+=1
  self.send_error(405)
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(label,p):
 checks.append(bool(p))
 print("PASS" if p else "FAIL",label)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   ctx=b.new_context(viewport={"width":width,"height":844})
   pg=ctx.new_page()
   errors=[]
   pg.on("pageerror",lambda e:errors.append(str(e)))
   response=pg.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=8&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",response.status==200)
   check(mode+"_questions",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 109","QUESTÃO 110","QUESTÃO 111"])
   check(mode+"_15_options",pg.locator(".page-question input[type=radio]").count()==15)
   opts=pg.locator(".page-question").first.locator(".page-q-option")
   check(mode+"_five_graphical_options",opts.count()==5 and
    opts.locator("img").count()==5)
   imgs=pg.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}))")
   check(mode+"_seven_native_images",len(imgs)==7 and all(x["loaded"] and "integral" not in x["src"] for x in imgs))
   compact=pg.locator("#page-reading-mode").count()==1
   check(mode+"_reading_mode",pg.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")==(compact and mode=="mobile"))
   check(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   qs=pg.locator(".page-question")
   for n,value in enumerate(("B","C","D")):
    qs.nth(n).locator(f"input[type=radio][value={value}]").check()
   pg.reload(wait_until="networkidle")
   qs=pg.locator(".page-question")
   check(mode+"_drafts_after_reload",all(qs.nth(n).locator(f"input[type=radio][value={value}]").is_checked() for n,value in enumerate(("B","C","D"))))
   check(mode+"_js_clean",not errors)
   shot=root/f"p008_render_{mode}.png"
   pg.screenshot(path=str(shot),full_page=True)
   print("SCREENSHOT_SHA",mode,hashlib.sha256(shot.read_bytes()).hexdigest())
   ctx.close()
  b.close()
finally:
 srv.shutdown()
check("no_POST",Handler.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
