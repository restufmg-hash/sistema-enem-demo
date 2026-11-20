from pathlib import Path
import hashlib,json,argparse
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument("--pdf",type=Path,help="PDF oficial privado; habilita cotejo geométrico com a fonte")
args=parser.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p010_layout.json").read_text(encoding="utf-8"))
assert layout["source"]["pdf_page_index"]==9 and layout["source"]["printed_page"]==10
assert [q["number"] for q in layout["questions"]]==[116,117,118]
assert len(layout["response_targets"])==15
for item in layout["media"].values():
 f=root/item["url"];assert hashlib.sha256(f.read_bytes()).hexdigest()==item["sha256"]
 assert item["source_pdf_page"]==10
if args.pdf:
 source=args.pdf
 assert hashlib.sha256(source.read_bytes()).hexdigest()==layout["source"]["sha256"]
 import pymupdf`n doc=pymupdf.open(str(source));assert len(doc)==32
 pg=doc[9]
 words=pg.get_text("words")
 for target in layout["response_targets"]:
  matches=[w for w in words if w[4]==target["label"] and abs(w[0]-target["bbox"][0])<.07 and abs(w[1]-target["bbox"][1])<.07]
  assert len(matches)==1,(target,matches)
 print("SOURCE_PASS PDF_SHA, 15_TARGETS, 2_NATIVE_IMAGES")
else:
 print("SOURCE_SHA_AND_COORDINATES_NOT_CHECKED: pass --pdf to verify original PDF")
class Handler(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*args):pass
 def do_POST(self):
  Handler.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(label,condition):
 checks.append(bool(condition));print(("PASS" if condition else "FAIL"),label)
try:
 with sync_playwright() as playwright:
  browser=playwright.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   context=browser.new_context(viewport={"width":width,"height":844})
   page=context.new_page();errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   r=page.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=10&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",r.status==200)
   check(mode+"_questions",page.locator(".page-question h2").all_inner_texts()==["QUESTÃO 116","QUESTÃO 117","QUESTÃO 118"])
   check(mode+"_options",page.locator(".page-question input[type=radio]").count()==15)
   assets=page.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}))")
   check(mode+"_native_assets",len(assets)==2 and all(x["loaded"] and "integral" not in x["src"] for x in assets))
   check(mode+"_reading_mode",page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")==(mode=="mobile"))
   check(mode+"_no_overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   qs=page.locator(".page-question")
   for i,opt in enumerate(("B","C","D")):qs.nth(i).locator(f"input[type=radio][value={opt}]").check()
   page.reload(wait_until="networkidle")
   qs=page.locator(".page-question")
   check(mode+"_drafts_after_reload",all(qs.nth(i).locator(f"input[type=radio][value={opt}]").is_checked() for i,opt in enumerate(("B","C","D"))))
   check(mode+"_js_clean",not errors)
   file=root/f"p010_{mode}.png";page.screenshot(path=str(file),full_page=True)
   print("SCREENSHOT_SHA",mode,hashlib.sha256(file.read_bytes()).hexdigest())
   context.close()
  browser.close()
finally:srv.shutdown()
check("zero_POST",Handler.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
