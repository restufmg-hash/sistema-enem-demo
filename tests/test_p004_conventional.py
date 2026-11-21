"""Página 6, ENEM 2024 D2 C5; usar --pdf para validação nativa de origem."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import argparse,hashlib,json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
arg=argparse.ArgumentParser();arg.add_argument("--pdf",type=Path)
args=arg.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p004_layout.json").read_text(encoding="utf-8"))
assert [q["number"] for q in layout["questions"]]==[98,99,100]
assert layout["source"]["pdf_page_index"]==3 and layout["source"]["printed_page"]==4
assert len(layout["response_targets"])==15 and len(layout["media"])==7
assert layout["layout"]["columns"][0]["order"]==[98,99]
assert layout["layout"]["columns"][1]["order"]==[100]
for tag,media in layout["media"].items():
 path=root/media["url"]
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==media["sha256"],tag
 assert media["source_pdf_page"]==4
if args.pdf:
 import pymupdf
 assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
 d=pymupdf.open(str(args.pdf));assert len(d)==32
 page=d[3]
 assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<.01
 assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<.01
 words=page.get_text("words")
 for t in layout["response_targets"]:
  matches=[w for w in words if w[4]==t["label"] and
   abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08]
  assert len(matches)==1,t
 original={hashlib.sha256(d.extract_image(x[0])["image"]).hexdigest() for x in page.get_images(full=True)}
 assert all(m["sha256"] in original for m in layout["media"].values())
 print("SOURCE_PASS PDF_SHA, 15_OPTION_COORDINATES, 7_NATIVE_MEDIA")
else:print("PDF_ORIGIN_NOT_CHECKED: provide --pdf")
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
server=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
passes=[]
def check(name,ok):
 passes.append(bool(ok));print("PASS" if ok else "FAIL",name)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   context=browser.new_context(viewport={"width":width,"height":844})
   pg=context.new_page();errors=[]
   pg.on("pageerror",lambda err:errors.append(str(err)))
   res=pg.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=4&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",res.status==200)
   check(mode+"_titles",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 98","QUESTÃO 99","QUESTÃO 100"])
   check(mode+"_columns",pg.locator(".page-columns").count()==1 and pg.locator(".page-column").count()==2)
   check(mode+"_options",pg.locator(".page-question input[type=radio]").count()==15)
   imgs=pg.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}))")
   check(mode+"_seven_images",len(imgs)==7 and all(z["loaded"] and "integral" not in z["src"] for z in imgs))
   q100=pg.locator(".page-question").last
   check(mode+"_five_vector_options",q100.locator(".page-q-option img").count()==5)
   check(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   check(mode+"_reading_state",pg.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")==(mode=="mobile" and pg.locator("#page-reading-mode").count()==1))
   for i,letter in enumerate("BCD"):pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").check()
   pg.reload(wait_until="networkidle")
   check(mode+"_draft_recovery",all(pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").is_checked() for i,letter in enumerate("BCD")))
   check(mode+"_no_js_errors",not errors)
   shot=root/f"p004_renderer_{mode}.png";pg.screenshot(path=str(shot),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(shot.read_bytes()).hexdigest())
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(passes),"/",len(passes))
assert all(passes)
