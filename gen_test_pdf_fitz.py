import fitz

def create_test_pdf(filename):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Este é um documento de teste para o sistema RAG.")
    page.insert_text((100, 120), "A faculdade de artes tem 3 professores: João, Maria e Pedro.")
    
    page2 = doc.new_page()
    page2.insert_text((100, 100), "Na página 2, falamos sobre as bibliotecas usadas.")
    page2.insert_text((100, 120), "Usamos Django, Celery, Redis e Gemini API.")
    
    doc.save(filename)
    doc.close()

if __name__ == "__main__":
    create_test_pdf("teste_projeto.pdf")
    print("PDF de teste criado via fitz: teste_projeto.pdf")
