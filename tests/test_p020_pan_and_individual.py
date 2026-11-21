"""Q147 math horizontal pan and Q148 source illustration + individual drafts."""
from pathlib import Path
from threading import Thread
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(n,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",n,flush=True)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True)
  pg=b.new_page(viewport={"width":390,"height":844});errors=[]
  pg.on("pageerror",lambda e:errors.append(str(e)))
  home=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=20&caderno=cdamarelo&cor=amarelo"
  pg.goto(home,wait_until="networkidle")
  pan=pg.locator(".page-question").first.locator(".page-option-pan")
  check("q147_five_pan_regions",pan.count()==5)
  check("q147_regions_keyboard_focus",pan.evaluate_all("(xs)=>xs.every(x=>x.tabIndex===0&&x.getAttribute('role')==='region')"))
  check("q147_regions_scrollable",pan.evaluate_all("(xs)=>xs.every(x=>x.scrollWidth>x.clientWidth+50)"))
  check("q147_img_original_dimensions",pg.locator(".page-question").first.locator(".page-option-pan img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>x.complete&&x.naturalWidth>1000)"))
  first=pan.first
  first.focus()
  check("q147_focus_works",first.evaluate("(x)=>document.activeElement===x"))
  check("q147_horizontal_scroll_works",first.evaluate("(x)=>{x.scrollLeft=130;return x.scrollLeft>=120}"))
  check("q147_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
  figure=pg.locator(".page-question").nth(1).locator("figure.wide-original")
  check("q148_wide_figure_region",figure.count()==1 and figure.first.get_attribute("tabindex")=="0")
  check("q148_source_png_loaded",figure.locator("img").evaluate("(x)=>x.complete&&x.naturalWidth===989&&x.naturalHeight===211"))
  for i,n,letter in ((0,147,"B"),(1,148,"D")):
   pg.locator(".page-question").nth(i).locator(f"input[value={letter}]").check()
   pg.locator(".page-question").nth(i).locator(".page-question-controls a").click()
   check(f"q{n}_individual_url",f"q{n}" in pg.url)
   check(f"q{n}_draft",pg.locator(f"#alternativas input[value={letter}]").is_checked())
   check(f"q{n}_five_options",pg.locator("#alternativas input[type=radio]").count()==5)
   if n==147:
    check("q147_five_math_images",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>x.complete&&x.naturalWidth>1000)"))
    check("q147_individual_five_pan_regions",pg.locator("#alternativas .option-individual-pan").count()==5)
    check("q147_individual_pan_keyboard",pg.locator("#alternativas .option-individual-pan").evaluate_all("(xs)=>xs.every(x=>x.tabIndex===0&&x.scrollWidth>x.clientWidth+50)"))
    check("q147_individual_no_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if n==148:
    check("q148_native_figure_individual",pg.locator("#enunciado-estruturado img").evaluate("(x)=>x.complete&&x.naturalWidth===989"))
   check(f"q{n}_no_full_crop",pg.locator("#figura").is_hidden())
   pg.goto(home,wait_until="networkidle")
  check("q147_and_q148_roundtrip",pg.locator(".page-question").first.locator("input[value=B]").is_checked() and pg.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
  check("no_js_errors",not errors)
  b.close()
finally:srv.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
