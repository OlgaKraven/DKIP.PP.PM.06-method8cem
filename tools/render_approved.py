"""Render the approved block and route PDF profile for PP PM.06."""
from pathlib import Path
import html,re
ESC=html.escape

def source_path(root,path):return root/path

def linkify(text):
    escaped=ESC(text)
    return re.sub(r'https://[^\s<]+',lambda m:'<link href="'+m[0].rstrip('.;,')+'" color="#a50b12"><u>'+m[0].rstrip('.;,')+'</u></link>'+m[0][len(m[0].rstrip('.;,')):],escaped)

def fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    assets=Path(__file__).resolve().parents[1]/'assets/fonts'
    for alias,name in [('Body','Regular'),('Semi','Semibold'),('Bold','Bold')]:
        pdfmetrics.registerFont(TTFont(alias,str(assets/f'GolosText-{name}.ttf')))
    choices=[Path('C:/Windows/Fonts/consola.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')]
    mono=next((p for p in choices if p.is_file()),None)
    if mono is None:raise ValueError('A monospaced font is required')
    pdfmetrics.registerFont(TTFont('Mono',str(mono)))
    symbols=Path('C:/Windows/Fonts/seguisym.ttf')
    if not symbols.is_file():symbols=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('Symbols',str(symbols)))


def pdf(root, target, data, section, release=False):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak, Image, Flowable, HRFlowable
    fonts()
    def E(text):
        return linkify(text).replace('✓','<font name="Symbols">✓</font>')
    W,H=210*mm,297*mm
    available=160*mm
    cwidth=available-33
    inner=cwidth-26
    body=ParagraphStyle('Body',fontName='Body',fontSize=10.5,leading=16,alignment=TA_LEFT,spaceAfter=6)
    heading=ParagraphStyle('Heading',fontName='Semi',fontSize=13,leading=18,spaceAfter=10)
    mono=ParagraphStyle('Mono',fontName='Mono',fontSize=8.5,leading=12,splitLongWords=True,wordWrap='CJK')
    caption=ParagraphStyle('Caption',fontName='Body',fontSize=9.5,leading=15,spaceAfter=0)
    title=ParagraphStyle('Title',fontName='Bold',fontSize=24,leading=28,textColor=colors.white,spaceAfter=0)
    kicker=ParagraphStyle('Kicker',fontName='Semi',fontSize=9,leading=13,textColor=colors.white,spaceAfter=0)
    check=ParagraphStyle('Check',parent=caption,spaceBefore=0)

    class Banner(Flowable):
        keepWithNext=True
        def __init__(self,label,name,key):
            Flowable.__init__(self)
            self.label=Paragraph(ESC(label),kicker)
            self.name=Paragraph(ESC(name),title)
            self.key=key
            self.outline=name
            self.label.wrap(available-36,1000)
            self.height=19+13+12+self.name.wrap(available-36,1000)[1]+20+4
            self.width=available
        def wrap(self,w,h):return self.width,self.height
        def draw(self):
            c=self.canv;c.setFillColor(colors.HexColor('#1c1c1c'));c.rect(0,0,self.width,self.height,fill=1,stroke=0)
            c.bookmarkPage(self.key);c.addOutlineEntry(self.outline,self.key,level=0,closed=False)
            c.setFillColor(colors.HexColor('#ed131c'));c.rect(0,0,self.width,4,fill=1,stroke=0)
            self.label.drawOn(c,18,self.height-19-13)
            h=self.name.wrap(available-36,1000)[1];self.name.drawOn(c,18,24)

    class Card(Flowable):
        def __init__(self,n,name,parts,continued=False):
            Flowable.__init__(self);self.n=n;self.name=name;self.parts=parts;self.continued=continued
            self.width=available;self.spaceAfter=13
            self.head=Paragraph(ESC(name)+(' — продолжение' if continued else ''),heading)
        def measures(self):
            self.hh=self.head.wrap(inner,10000)[1]
            self.hs=[p.wrap(inner,10000)[1]+p.getSpaceAfter() for p in self.parts]
            return 26+self.hh+10+sum(self.hs)
        def wrap(self,w,h):self.height=self.measures();return self.width,self.height
        def split(self,w,h):
            if self.measures() <= H-40*mm:
                return []
            if h<155:return []
            fixed=26+self.head.wrap(inner,10000)[1]+10
            used=fixed;first=[];rest=[]
            for i,p in enumerate(self.parts):
                ph=p.wrap(inner,10000)[1]+p.getSpaceAfter()
                if used+ph<=h:
                    first.append(p);used+=ph;continue
                split=p.split(inner,h-used-p.getSpaceAfter()) if h-used>=32 else []
                if split:
                    first.append(split[0]);rest=split[1:]+self.parts[i+1:]
                else:rest=self.parts[i:]
                break
            if not first or not rest:return []
            return [Card(self.n,self.name,first,self.continued),Card(self.n,self.name,rest,True)]
        def draw(self):
            self.measures();c=self.canv
            c.setStrokeColor(colors.HexColor('#dfe1e5'));c.setLineWidth(.6);c.line(12,0,12,self.height-35)
            c.setFillColor(colors.HexColor('#f4f4f6'));c.roundRect(33,0,cwidth,self.height,10,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#ed131c'));c.setLineWidth(1.1);c.circle(12,self.height-24,11,fill=1,stroke=1)
            c.setFillColor(colors.HexColor('#1c1c1c'));c.setFont('Body',9);c.drawCentredString(12,self.height-27,str(self.n))
            y=self.height-13-self.hh;self.head.drawOn(c,46,y);y-=10
            for p,ph in zip(self.parts,self.hs):
                height=p.wrap(inner,10000)[1];y-=height;p.drawOn(c,46,y);y-=p.getSpaceAfter()

    def paras(text,style=body):
        return [Paragraph(E(x).replace('\n','<br/>'),style) for x in text.split('\n\n') if x.strip()]
    figure=0
    def card(n,block):
        nonlocal figure
        parts=[]
        if block['kind']=='image':
            figure+=1
            image=Image(str(source_path(root,block['path'])))
            image._restrictSize(inner,250)
            parts=[image,Spacer(1,8),Paragraph('Рисунок '+str(figure)+' — '+ESC(block['text']),caption)]
        elif block['kind']=='link':
            parts=[Paragraph('<link href="'+ESC(block['url'],quote=True)+'" color="#a50b12"><u>'+ESC(block['text'])+'</u></link>',body)]
        elif block['kind'] in {'code','listing'}:
            for line in block['text'].split('\n'):
                text=ESC(line.expandtabs(4)).replace(' ','&#160;').replace('✓','<font name="Symbols">✓</font>')
                parts.append(Paragraph(text or '&#160;',mono))
        else:
            parts=paras(block['text'])
            if block.get('url'):
                parts.append(Paragraph('<link href="'+ESC(block['url'],quote=True)+'" color="#a50b12"><u>'+ESC(block['link_label'])+'</u></link>',body))
            if block.get('check_text'):
                parts.extend([Spacer(1,14),HRFlowable(width=inner,thickness=.6,color=colors.HexColor('#dfe1e5'),spaceAfter=11)])
                parts.extend(paras(block['check_text'],caption))
            if 'провер' in block['title'].lower():
                parts=[HRFlowable(width=inner,thickness=.6,color=colors.HexColor('#dfe1e5'),spaceAfter=11)]+parts
        return Card(n,block['title'],parts)


    specs=data['assignment']+data['guide'] if section=='assignment' else data['areas']
    label='Методические рекомендации' if section=='assignment' else 'Список предметных областей'
    story=[]
    for i,page in enumerate(specs,1):
        if story:story.append(PageBreak() if section=='guide' else Spacer(1,18))
        tag='ПП ПМ.06 · '+('Вариант '+str(i).zfill(2) if section=='guide' else label)
        gap=Spacer(1,18);gap.keepWithNext=True
        story.extend([Banner(tag,page['title'],f'{section}-{i}'),gap])
        for n,block in enumerate(page['blocks'],1):story.append(card(n,block))
    def footer(c,doc):
        c.saveState();c.setFillColor(colors.HexColor('#606773'));c.setFont('Body',8);c.drawCentredString(W/2,10*mm,str(doc.page));c.restoreState()
    doc=BaseDocTemplate(str(target),pagesize=(W,H),leftMargin=30*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=20*mm,title=label+' — ПМ.06',author='',invariant=1)
    frame=Frame(30*mm,20*mm,160*mm,H-40*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='page',frames=[frame],onPage=footer))
    doc.build(story)


def build(root,data):
    pdf(root,root/'downloads/assignment.pdf',data,'assignment')
    pdf(root,root/'downloads/guide.pdf',data,'guide')
