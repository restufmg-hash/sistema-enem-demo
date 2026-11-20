"""Teste independente da página 7 convencional Q107/Q108 sem gabarito.
Execute: python tests/test_p007_single_column.py [--pdf /path/2024_PV_impresso_D2_CD5.pdf]
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
import argparse,hashlib,json
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--pdf",type=Path)
args=parser.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p007_layout.json").read_text(encoding="utf-8"))
assert layout["layout"]["mode"]=="single_column" and len(layout["layout"]["columns"])==1
assert layout["layout"]["columns"][0]["order"]==[107,108]
assert len(layout["response_targets"])==10 and len(layout["media"])==1
source=next(iter(layout["media"].values()))
img=root/source["url"]
assert hashlib.sha256(img.read_bytes()).hexdigest()==source["sha256"]
assert source["source_pdf_page"]==7
assert [q["number"] for q in layout["questions"]]==[107,108]
if args.pdf:
 import pymupdf
 assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
 doc=pymupdf.open(str(args.pdf))
 assert len(doc)==32
 page=doc[6]
 assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<.01
 assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<.01
 words=page.get_text("words")
 for target in layout["response_targets"]:
  matches=[w for w in words if w[4]==target["label"] and
           abs(w[0]-target["bbox"][0])<.07 and abs(w[1]-target["bbox"][1])<.07]
  assert len(matches)==1,target
 xrefs=[x[0] for x in page.get_images(full=True) if
        hashlib.sha256(doc.extract_image(x[0])["image"]).hexdigest()==source["sha256"]]
 assert xrefs==[61],xrefs
 print("PASS SOURCE SHA256, TEN NATIVE TARGETS, ORIGINAL XREF61")
else:
 print("SOURCE PDF NOT CHECKED; supply --pdf for full source validation")
checks=[]
def check(label,ok):
 checks.append(bool(ok))
 print("PASS" if ok else "FAIL",label)
class H(SimpleHTTPRequestHandler):
 posts=0
 def do_POST(self):H.posts+=1;self.send_error(405)
 def log_message(self,*a):pass
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   ctx=browser.new_context(viewport={"width":width,"height":844})
   page=ctx.new_page();errors=[]
   page.on("pageerror",lambda err:errors.append(str(err)))
   res=page.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=7&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",res.status==200)
   check(mode+"_heading",page.locator(".page-question h2").all_inner_texts()==["QUESTÃO 107","QUESTÃO 108"])
   check(mode+"_single_column",page.locator(".page-columns.single-column").count()==1 and page.locator(".page-column").count()==1)
   check(mode+"_answer_controls",page.locator(".page-question input[type=radio]").count()==10)
   check(mode+"_original_figure",page.locator("#page-sheet img").count()==1 and
         page.locator("#page-sheet img").first.evaluate("(im)=>im.complete&&im.naturalWidth===1335"))
   check(mode+"_image_scales_within_content",page.locator("#page-sheet img").first.evaluate(
       "(im)=>im.getBoundingClientRect().width<=im.parentElement.parentElement.getBoundingClientRect().width+1"))
   check(mode+"_no_x_overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile" and page.locator("#page-viewport.read-mode").count():
    fig=page.locator(".page-question figure.wide-original")
    check("mobile_wide_fig_focusable",fig.get_attribute("tabindex")=="0")
    check("mobile_figure_legible_pan",fig.evaluate(
      "(el)=>el.scrollWidth>el.clientWidth+200 && parseFloat(getComputedStyle(el.querySelector('img')).width)>=800"))
    check("mobile_figure_pan_operates",fig.evaluate("(el)=>{el.scrollLeft=150;return el.scrollLeft>100}"))
   check(mode+"_visible_content",page.locator(".page-question").last.inner_text().find("97,4%")>=0 and
         page.locator(".page-question").first.inner_text().find("mercúrio")>=0)
   selectable=page.locator(".page-question")
   selectable.nth(0).locator("input[value=B]").check()
   selectable.nth(1).locator("input[value=D]").check()
   page.reload(wait_until="networkidle")
   check(mode+"_drafts",page.locator(".page-question").nth(0).locator("input[value=B]").is_checked() and
         page.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
   check(mode+"_no_js_error",not errors)
   file=root/f"p007_renderer_{mode}.png"
   page.screenshot(path=str(file),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(file.read_bytes()).hexdigest())
   ctx.close()
  browser.close()
finally:srv.shutdown()
check("zero_post",H.posts==0)
print("TOTAL",sum(checks),"/",len(checks))
assert all(checks)
