"""Script para converter fotos dos integrantes em base64 e gerar o bloco HTML da seção de equipe."""
import base64, os

fotos = {
    "Diego Rodrigues":       ("foto diego.jpeg",  "Engenharia de Sistemas",         "https://www.linkedin.com/in/diego-rodrigues-7b8330112"),
    "Diogo Santos":          ("foto diogo.jpeg",   "Engenharia de Confiabilidade",   "https://www.linkedin.com/in/diogo-santos-a3a25b205"),
    "Gleyson Santos":        ("foto gleyson.jpeg", "Operação Offshore",              "https://www.linkedin.com/in/gleyson-santos1990"),
    "Kellvin Moura":         ("foto kelvin.jpeg",  "Automação & IoT",                "https://www.linkedin.com/in/kellvin-moura"),
    "Thiago Augusto Santos": ("foto thiago.jpeg",  "Análise de Dados",               "https://www.linkedin.com/in/thiago-augusto-santos-462756251"),
}

base_dir = r"c:\Users\DIEGO\Documents\PROJETO FLOTADOR"

cards = []
for nome, (arq, cargo, li) in fotos.items():
    path = os.path.join(base_dir, arq)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = "jpeg" if arq.endswith(".jpeg") else "png"
    cards.append((nome, cargo, li, b64, ext))

# Gera o HTML dos cards
html_cards = ""
for nome, cargo, li, b64, ext in cards:
    html_cards += f"""
    <div class="team-card">
      <div class="team-photo-wrap">
        <img src="data:image/{ext};base64,{b64}" alt="{nome}" class="team-photo" />
        <a href="{li}" target="_blank" rel="noopener" class="li-btn" title="LinkedIn de {nome}">
          <svg viewBox="0 0 24 24" fill="white" width="16" height="16"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
        </a>
      </div>
      <div class="team-info">
        <div class="team-name">{nome}</div>
        <div class="team-role">{cargo}</div>
      </div>
    </div>"""

print(html_cards)
