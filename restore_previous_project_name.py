from docx import Document


DOCX = "ModuleNew.docx"
OLD_NAME = "TLaser：光通讯激光器7D即时预测与L-I-V在线标定SaaS"
PREVIOUS_NAME = "光通讯激光器数字孪生技术"


doc = Document(DOCX)
changed = 0
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            if OLD_NAME in cell.text:
                cell.text = cell.text.replace(OLD_NAME, PREVIOUS_NAME)
                changed += 1

doc.save(DOCX)
print(f"changed_cells={changed}")
