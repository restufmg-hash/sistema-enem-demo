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
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p016_layout.json").read_text(encoding="utf-8"))
assert [q["number"] for q in layout["questions"]]==[136,137,138,139]
assert layout["source"]["pdf_page_index"]==15 and layout["source"]["printed_page"]==16
assert len(layout["response_targets"])==20 and len(layout["media"])==7
assert layout["layout"]["columns"][0]["order"]==[136,137]
assert layout["layout"]["columns"][1]["order"]==[138,139]
for tag,media in layout["media"].items():
 path=root/media["url"]
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==media["sha256"],tag
 assert media["source_pdf_page"]==16
if args.pdf:
 import pymupdf
 assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
 d=pymupdf.open(str(args.pdf));assert len(d)==32
 page=d[15]
 assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<.01
 assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<.01
 words=page.get_text("words")
 for t in layout["response_targets"]:
  matches=[w for w in words if w[4]==t["label"] and
   abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08]
  assert len(matches)==1,t
 for key,item in layout["media"].items():
  raster=page.get_pixmap(matrix=pymupdf.Matrix(item["render_scale"],item["render_scale"]),clip=pymupdf.Rect(item["source_bbox"]),alpha=False).tobytes("png")
  assert hashlib.sha256(raster).hexdigest()==item["sha256"],key
 print("SOURCE_PASS PDF_SHA, 20_OPTION_COORDINATES, SEVEN_PDF_VECTOR_CROPS")
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
   res=pg.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=16&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",res.status==200)
   check(mode+"_titles",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 136","QUESTÃO 137","QUESTÃO 138","QUESTÃO 139"])
   check(mode+"_columns",pg.locator(".page-columns").count()==1 and pg.locator(".page-column").count()==2)
   check(mode+"_options",pg.locator(".page-question input[type=radio]").count()==20)
   imgs=pg.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}))")
   check(mode+"_three_images",len(imgs)==7 and all(z["loaded"] and "integral" not in z["src"] for z in imgs))
   check(mode+"_source_figures_in_sections",
     pg.locator(".page-question").nth(0).locator("img").count()==1 and
     pg.locator(".page-question").nth(1).locator("img").count()==1 and
     pg.locator(".page-question").nth(2).locator("img").count()==0 and
     pg.locator(".page-question").nth(3).locator(".page-q-option img").count()==5)
   check(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile" and pg.locator("#page-viewport.read-mode").count():
    images=pg.locator(".page-question").last.locator(".page-q-option.visual img")
    check("mobile_q139_five_graphics_fit",images.count()==5 and images.evaluate_all(
     "(xs)=>xs.every(im=>{const r=im.getBoundingClientRect(),p=im.closest('.page-q-option').getBoundingClientRect();return r.left>=p.left&&r.right<=p.right+1&&r.width>=70;})"))
    check("mobile_read_mode_required",pg.locator("#page-reading-mode").count()==1)

   check(mode+"_reading_state",pg.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")==(mode=="mobile" and pg.locator("#page-reading-mode").count()==1))
   for i,letter in enumerate("BCDE"):pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").check()
   pg.reload(wait_until="networkidle")
   check(mode+"_draft_recovery",all(pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").is_checked() for i,letter in enumerate("BCDE")))
   check(mode+"_no_js_errors",not errors)
   shot=root/f"p016_renderer_{mode}.png";pg.screenshot(path=str(shot),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(shot.read_bytes()).hexdigest())
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(passes),"/",len(passes))
assert all(passes)
