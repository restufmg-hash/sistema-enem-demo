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
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p005_layout.json").read_text(encoding="utf-8"))
assert [q["number"] for q in layout["questions"]]==[101,102,103]
assert layout["source"]["pdf_page_index"]==4 and layout["source"]["printed_page"]==5
assert len(layout["response_targets"])==15 and len(layout["media"])==3
assert layout["layout"]["columns"][0]["order"]==[101,102]
assert layout["layout"]["columns"][1]["order"]==[103]
for tag,media in layout["media"].items():
 path=root/media["url"]
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==media["sha256"],tag
 assert media["source_pdf_page"]==5
if args.pdf:
 import pymupdf
 assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
 d=pymupdf.open(str(args.pdf));assert len(d)==32
 page=d[4]
 assert abs(page.rect.width-layout["source"]["pdf_width_pt"])<.01
 assert abs(page.rect.height-layout["source"]["pdf_height_pt"])<.01
 words=page.get_text("words")
 for t in layout["response_targets"]:
  matches=[w for w in words if w[4]==t["label"] and
   abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08]
  assert len(matches)==1,t
 original={hashlib.sha256(d.extract_image(x[0])["image"]).hexdigest() for x in page.get_images(full=True)}
 assert all(m["sha256"] in original for m in layout["media"].values() if m["source_role"]!="Tabela original das etapas I–VI do ciclo de Otto; imagem recortada da página PDF")
 assert (page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(291,307,536,512),alpha=False).tobytes("png") == (root/layout["media"]["q103-table"]["url"]).read_bytes())
 print("SOURCE_PASS PDF_SHA, 15_OPTION_COORDINATES, TWO_NATIVE_MEDIA_AND_TABLE_CROP")
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
   res=pg.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=5&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",res.status==200)
   check(mode+"_titles",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 101","QUESTÃO 102","QUESTÃO 103"])
   check(mode+"_columns",pg.locator(".page-columns").count()==1 and pg.locator(".page-column").count()==2)
   check(mode+"_options",pg.locator(".page-question input[type=radio]").count()==15)
   imgs=pg.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}))")
   check(mode+"_three_figures",len(imgs)==3 and all(z["loaded"] and "integral" not in z["src"] for z in imgs))
   q103=pg.locator(".page-question").last
   check(mode+"_q103_chart_and_table",q103.locator("img").count()==2)
   check(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   check(mode+"_reading_state",pg.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")==(mode=="mobile" and pg.locator("#page-reading-mode").count()==1))
   for i,letter in enumerate("BCD"):pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").check()
   pg.reload(wait_until="networkidle")
   check(mode+"_draft_recovery",all(pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").is_checked() for i,letter in enumerate("BCD")))
   check(mode+"_no_js_errors",not errors)
   shot=root/f"p005_renderer_{mode}.png";pg.screenshot(path=str(shot),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(shot.read_bytes()).hexdigest())
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(passes),"/",len(passes))
assert all(passes)
