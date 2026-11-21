"""ENEM 2024 D2 C5 p021 Q149/Q150: PDF vector provenance and HTTP visual."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import json,hashlib,argparse,pymupdf
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
arg=argparse.ArgumentParser();arg.add_argument("--pdf",type=Path,required=True);args=arg.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p021_layout.json").read_text(encoding="utf8"))
assert [q["number"] for q in layout["questions"]]==[149,150]
assert layout["layout"]["mode"]=="single_column" and layout["layout"]["columns"][0]["order"]==[149,150]
assert layout["source"]["printed_page"]==21 and layout["source"]["pdf_page_index"]==20
assert len(layout["media"])==7 and len(layout["response_targets"])==10
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
pdf=pymupdf.open(str(args.pdf));assert len(pdf)==32;page=pdf[20]
words=page.get_text("words")
for t in layout["response_targets"]:
 found=[w for w in words if w[4]==t["label"] and abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08]
 assert len(found)==1,(t,found)
for key,m in layout["media"].items():
 assert m["source_pdf_page"]==21 and m["source_kind"]=="pdf_vector_crop"
 path=root/m["url"];assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==m["sha256"],key
 raw=page.get_pixmap(matrix=pymupdf.Matrix(m["render_scale"],m["render_scale"]),clip=pymupdf.Rect(m["source_bbox"]),alpha=False).tobytes("png")
 assert hashlib.sha256(raw).hexdigest()==m["sha256"],key
q149=json.loads((root/layout["questions"][0]["source_data"]).read_text(encoding="utf-8-sig"))
q150=json.loads((root/layout["questions"][1]["source_data"]).read_text(encoding="utf-8-sig"))
assert q149["question_id"].endswith("q149") and q150["question_id"].endswith("q150")
assert [a["label"] for a in q149["options"]]==list("ABCDE")
assert all(x["image_only"] and x["pan_image"] and x["asset"]==layout["media"]["q149-"+x["label"]]["url"] for x in q149["options"])
assert [a["text"] for a in q150["options"]]==["5,4.","6,2.","7,6.","8,2.","8,4."]
assert len([b for b in q149["blocks"] if b["type"]=="image"])==1
assert len([b for b in q150["blocks"] if b["type"]=="image"])==1
assert 368 in [i[0] for i in page.get_images(full=True)]
print("SOURCE_PASS PDF_SHA 10_OPTION_POSITIONS 7_VECTOR_REPRODUCIBLE 2_QUESTIONS",flush=True)
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*args):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(name,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",name,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   context=browser.new_context(viewport={"width":width,"height":844})
   pg=context.new_page();errors=[]
   pg.on("pageerror",lambda e:errors.append(str(e)))
   res=pg.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=21&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_http200",res.status==200)
   check(mode+"_titles",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 149","QUESTÃO 150"])
   check(mode+"_one_column",pg.locator(".page-columns.single-column .page-column").count()==1)
   check(mode+"_ten_options",pg.locator(".page-question input[type=radio]").count()==10)
   check(mode+"_seven_images",pg.locator(".page-question img").evaluate_all("(xs)=>xs.length===7&&xs.every(x=>x.complete&&x.naturalWidth>0)"))
   check(mode+"_caesar_diagram",pg.locator(".page-question").first.locator("figure img").count()==1)
   check(mode+"_five_math_options",pg.locator(".page-question").first.locator(".page-q-option img").count()==5)
   check(mode+"_richter_equation",pg.locator(".page-question").nth(1).locator("figure img").count()==1)
   check(mode+"_richter_is_compact",pg.locator(".page-question").nth(1).locator("figure.compact-equation").count()==1 and
         pg.locator(".page-question").nth(1).locator("figure.wide-original").count()==0)
   check(mode+"_richter_fits_without_pan",pg.locator(".page-question").nth(1).locator("figure.compact-equation img").evaluate(
         "(x)=>{let r=x.getBoundingClientRect(),p=x.closest('.page-question').getBoundingClientRect();return r.width>170&&r.left>=p.left&&r.right<=p.right+1;}"))

   check(mode+"_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile":
    check("mobile_reading_mode",pg.locator("#page-viewport.read-mode").count()==1)
    check("mobile_five_pan_regions",pg.locator(".page-question").first.locator(".page-option-pan").count()==5)
    check("mobile_pan_focus",pg.locator(".page-question").first.locator(".page-option-pan").evaluate_all("(xs)=>xs.every(x=>x.tabIndex===0&&x.scrollWidth>x.clientWidth+40)"))
    check("mobile_wide_diagram",pg.locator(".page-question").first.locator("figure.wide-original").count()==1)
   for idx,label in enumerate(("C","D")):pg.locator(".page-question").nth(idx).locator(f"input[value={label}]").check()
   pg.reload(wait_until="networkidle")
   check(mode+"_drafts_recovered",pg.locator(".page-question").first.locator("input[value=C]").is_checked() and pg.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
   check(mode+"_no_page_errors",not errors)
   img=root/f"p021_renderer_{mode}.png";pg.screenshot(path=str(img),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(img.read_bytes()).hexdigest(),flush=True)
   context.close()
  browser.close()
finally:srv.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
