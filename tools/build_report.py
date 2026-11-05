from pathlib import Path
from copy import deepcopy
import shutil,hashlib,json,zipfile
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm
from docx.enum.table import WD_ROW_HEIGHT_RULE
import report_parts as parts
ROOT=Path(__file__).resolve().parents[1]
def text(e):return ''.join(t.text or '' for t in e.iter(qn('w:t')))
def labels(table,values,tag):
    original=deepcopy(table.rows[1]._tr)
    while len(table.rows)<len(values)+1:table._tbl.append(deepcopy(original))
    while len(table.rows)>len(values)+1:table._tbl.remove(table.rows[-1]._tr)
    for i,value in enumerate(values,1):
        for j,cell in enumerate(table.rows[i].cells):
            controls=cell._tc.xpath('.//w:sdt')
            for k,c in enumerate(controls):
                c.find('w:sdtPr/w:tag',c.nsmap).set(qn('w:val'),f'{tag}_{i}_{j}_{k}')
                ts=list(c.find(qn('w:sdtContent')).iter(qn('w:t')));ts[0].text=value if j==0 else '____________'
                for t in ts[1:]:t.text=''
            if j==0 and not controls:
                ts=cell._tc.xpath('.//w:t');ts[0].text=value
                for t in ts[1:]:t.text=''
    for row in table.rows:row.height=Mm(12);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST

def build():
    master=ROOT/'forms/template/Отчет о выполнении.docx';target=ROOT/'forms/Отчет о выполнении.docx';shutil.copyfile(master,target);doc=Document(target)
    for c in doc.element.xpath('.//w:sdt'):
        tag=c.find('w:sdtPr/w:tag',c.nsmap)
        if tag is not None and tag.get(qn('w:val'))=='practice_name':
            ts=list(c.find(qn('w:sdtContent')).iter(qn('w:t')));ts[0].text='Сопровождение информационных систем (ПМ.06)'
            for t in ts[1:]:t.text=''
    labels(doc.tables[0],['Номер и область; учебная или реальная организация','Готовый стенд, контракт и исходная коллекция','Данные, контрольная дата, три исходных ID','Резервная копия и место хранения'],'inputs')
    labels(doc.tables[1],['Windows и PowerShell','.NET SDK 10 и адрес своего API','Python 3 и отдельный тестовый проект','Редактор, Word и PowerPoint'],'environment')
    labels(doc.tables[2],['Область образца → собственная область','2027-03-04 → конечная дата своего варианта','101, 102, 103 → три собственных ID','Роли и SLA → собственная модель'],'mapping')
    doc.tables[1]._tbl.getprevious().get_or_add_pPr().append(parts.el('pageBreakBefore'))
    labels(doc.tables[-1],['Объект и границы модели описаны','Роли, RACI и каналы определены','14 процессов и фактическая сумма согласованы','SLA объявлен до измерения','Три ситуации разобраны без выдуманных наблюдений','Контрпример выявляет исходный дефект','Локальное изменение и откат проверены','Коллекция и данные согласованы','Копия, отказ и восстановление подтверждены','Показатели рассчитаны по реальным событиям','Схемы и инструкция пользователю подготовлены','Индивидуальное изменение и чистый повтор выполнены','Репозиторий и официальные формы доступны'],'final')
    stages=[
      ('Объект эксплуатации','Заполнить паспорт: назначение, функции, данные, пользователи, инфраструктура, режим, критичность и факторы сопровождения. Отличить учебную модель от реального предприятия.',['Контекстная схема системы и среды']),
      ('Организация сопровождения','Описать пять ролей, RACI, 14 процессов с входами/выходами/ответственными, каналы, единую регистрацию и SLA.',['Схема ролей и эскалации','Взаимосвязь процессов сопровождения']),
      ('Инциденты и изменение','Разобрать INC-01, INC-02 и REQ-03; сохранить гипотезу и подтверждение, CR-01, риск/согласование/откат, тесты до и после, собственное изменение и затронутую инструкцию.',['Жизненный цикл обращения','Процедура управления изменением','Исходный граничный ответ','Причина и локальная правка','Ответ после исправления','Результат индивидуального изменения']),
      ('Непрерывность и качество','Описать копии, восстановление, мониторинг, пороги, фактические отметки и формулы. Сравнить результаты с SLA, объяснить ограничения измерений и две меры улучшения.',['Процедура восстановления','Отказ данных и готовности','Восстановленные данные','Журнал событий и показатели','Чистый повтор'])]
    body=doc.element.body;children=list(body);start=next(i for i,e in enumerate(children) if text(e)=='Этап выполнения работы');end=next(i for i,e in enumerate(children) if text(e)=='Итоговая проверка и сдача');anchor=children[end]
    for e in children[start:end]:body.remove(e)
    fig=0;parts.CONTROL_ID=12000
    for i,(title,prompt,captions) in enumerate(stages,1):
        first=len(list(body))-1
        parts.heading(doc,title,level=2,new_page=i>1);doc.add_paragraph(prompt)
        for label,tag,lines in [('Исходные данные и ожидаемый результат','initial',2),('Выполненные действия','actions',3),('Фактический результат и проверка','actual',3),('Вывод по этапу и объяснение расхождений','conclusion',2)]:parts.response(doc,label,f's{i}_{tag}',lines)
        if i==2:tables=[('матрица ответственности',['Процесс','Пользователь','Поддержка','Специалист','Админ.','Руков.'],6),('процессы сопровождения',['Процесс','Класс','Вход','Выход','Ответственный'],14),('регламент реакции',['Приоритет','Влияние','Реакция, мин','Восстановление, мин'],3)]
        elif i==3:tables=[('карточки ситуаций',['Номер','Симптом и вход','Ожидание / факт','Причина и доказательство','Действие / итог'],3),('проверка изменения',['Случай','Вход','Ожидание','До','После'],9),('запрос изменения',['Цель и область','Риск и согласование','Копия / откат','Критерий приёмки'],2)]
        elif i==4:tables=[('регламент копирования',['Объект','Момент / период','Место / срок','Ответственный','Проверка'],5),('показатели качества',['Показатель','События / формула','Факт и единица','Предел','Вывод'],5)]
        else:tables=[]
        for caption,headers,rows in tables:
            doc.add_page_break();para=doc.add_paragraph(style='Table caption');para.add_run('Таблица ');parts.field(para,r'SEQ Таблица \* ARABIC','4');para.add_run(' — '+caption)
            table=doc.add_table(rows=rows+1,cols=len(headers));table.autofit=False
            borders=parts.el('tblBorders')
            for side in ['top','left','bottom','right','insideH','insideV']:borders.append(parts.el(side,val='single',sz=4,color='000000'))
            table._tbl.tblPr.append(borders)
            for j,h in enumerate(headers):table.cell(0,j).text=h
            for row in table.rows:
                row.height=Mm(13);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
                for cell in row.cells:
                    cell.width=Mm(160/len(headers))
                    for para in cell.paragraphs:para.style='Table text'
            table.rows[0]._tr.get_or_add_trPr().append(parts.el('tblHeader'))
        doc.add_page_break();para=doc.add_paragraph('Подтверждения этапа приведены на рис. ')
        for j,label in enumerate(captions):
            if j:para.add_run(', ')
            parts.field(para,f'REF pp064_fig_{fig+j+1} \\h',str(fig+j+1))
        para.add_run('. Вставить собственные материалы.')
        for j,label in enumerate(captions):
            if j and j%2==0:doc.add_page_break()
            fig+=1;parts.figure_slot(doc,label,f'pp064_picture_{fig}',fig,f'pp064_fig_{fig}')
        for el in list(body)[first:-1]:body.remove(el);anchor.addprevious(el)
    for cid,c in enumerate(doc.element.xpath('.//w:sdt'),31000):c.find('w:sdtPr/w:id',c.nsmap).set(qn('w:val'),str(cid))
    for row in doc.tables[-1].rows:row.height=Mm(9);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
    for level in doc.part.numbering_part.element.findall('.//'+qn('w:lvl')):
        suffix=level.find(qn('w:suff'))
        if suffix is not None:suffix.set(qn('w:val'),'nothing')
        rpr=level.find(qn('w:rPr'))
        if rpr is None:rpr=parts.el('rPr');level.append(rpr)
        font=rpr.find(qn('w:rFonts'))
        if font is None:font=parts.el('rFonts');rpr.append(font)
        for attr in ['ascii','hAnsi','eastAsia','cs']:font.set(qn('w:'+attr),'Times New Roman')
        for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:font.attrib.pop(qn('w:'+attr),None)
    for para in doc.paragraphs:
        if para.style.name.startswith('Heading') and para.runs:para.runs[0].text=' '+para.runs[0].text
        if para.text=='Состав передаваемых материалов':para.paragraph_format.page_break_before=True
    doc.core_properties.title='Отчет о выполнении';doc.core_properties.author=doc.core_properties.last_modified_by='';doc.core_properties.comments='';doc.save(target)
    shutil.copyfile(target,ROOT/'downloads/Отчет о выполнении.docx')
    (ROOT/'content/report-origin.json').write_text(json.dumps(dict(master_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),stages=4,figures=fig),indent=2),encoding='utf-8')
    print('Report copied from master:',fig,'figure frames')
if __name__=='__main__':build()
