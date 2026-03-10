from reportlab.pdfgen import canvas

def create_test_pdf(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Este é um documento de teste para o sistema RAG.")
    c.drawString(100, 730, "A faculdade de artes tem 3 professores: João, Maria e Pedro.")
    c.drawString(100, 710, "Cada professor gerencia sua própria base de dados de arquivos.")
    c.showPage()
    c.drawString(100, 750, "Na página 2, falamos sobre as bibliotecas usadas.")
    c.drawString(100, 730, "Usamos Django, Celery, Redis e Gemini API.")
    c.save()

if __name__ == "__main__":
    create_test_pdf("teste_projeto.pdf")
    print("PDF de teste criado: teste_projeto.pdf")
