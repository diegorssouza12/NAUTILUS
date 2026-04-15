import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import pdfplumber
import re
import base64
import os
import io
from datetime import datetime, timedelta
import altair as alt
import plotly.graph_objects as go
import plotly.subplots as sp
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

st.set_page_config(page_title="Nautilus", page_icon="🌊", layout="wide")

DB_FILE = "manutencao.db"

# ─────────────────────────────────────────────────────────────────────────────
# BASE DE CONHECIMENTO DO ASSISTENTE LLM (Respostas pré-mapeadas por perfil)
# ─────────────────────────────────────────────────────────────────────────────
LLM_QA_OPERACAO = [
    {
        "pergunta": "Qual o status do processo de comissionamento do MCC?",
        "resposta": (
            "🔧 **Comissionamento — MCC (Compressor Novo)**\n\n"
            "O equipamento atingiu rotação de teste (5.200 RPM), mas apresentou **alta vibração (95 µm)** no mancal DE. Diferença de 4,5x em relação ao mancal NDE (21 µm).\n\n"
            "**Diagnóstico:** Desbalanceamento assimétrico severo ou desalinhamento interno. A recomendação do plano de ação é a realização de *swapping* dos módulos HP ou realinhamento a laser. Não acelerar rampa de carga rotativa até autorização.\n\n"
            "⚠️ Plataforma de Destino: **FPSO FORTE (PRIO)**."
        )
    },
    {
        "pergunta": "Quais equipamentos estão em estado crítico agora?",
        "resposta": (
            "🚨 **Status Crítico dos Ativos — Varredura FPSO FORTE**\n\n"
            "Baseado nos últimos alarmes SCADA/Vibração:\n\n"
            "| TAG | Equipamento | Vibração (DE) | TAN (Óleo) | Status |\n"
            "|-----|-------------|---------------|------------|--------|\n"
            "| MCA | Compressor de Gás Natural (HP) | **91,4 µm** ⚠️ | **0,67** ⚠️ | 🔴 Crítico |\n"
            "| MCB | Compressor de Gás Natural | 0,0 µm | Normal | ⚫ Indisponível (Desligado) |\n\n"
            "**Recomendação:** Ação mitigadora de diálise/filtragem de óleo no **MCA** para baixar a contagem de partículas (atualmente 12.908 em 4µm - Classe Crítica). Cuidado risco faliar mancal patente."
        )
    },
    {
        "pergunta": "Como devo proceder com o MCB que está fora de operação?",
        "resposta": (
            "🔍 **Diagnóstico — MCB (Indisponível)**\n\n"
            "A máquina estrutural e mecânica encontra-se sadia, mas está impossibilitada de operar por **falha crítica nos Transformadores de Alimentação (Trafos)**.\n\n"
            "**Plano Imediato (Logística):** Avaliar procedimento de 'Canibalização Elétrica' retirando os transformadores do MCC e montando no MCB, para garantir redundância para o MCA.\n\n"
            "📌 A autorização depende da engenharia de manutenção embarcada."
        )
    },
    {
        "pergunta": "Quais as indicações no evento de aumento de acidez do óleo lubrificante no MCA?",
        "resposta": (
            "🛑 **Anomalia de Fluido — MCA**\n\n"
            "Detectamos a elevação no Índice TAN (Acidez) de **0,30 para 0,67**, configurando oxidação ácida severa. Também há aumento abrupto de Cobre (Cu) e Ferro (Fe) na espectrometria.\n\n"
            "**Ações Imediatas:**\n"
            "1. Instalar unidade externa de diálise termográfica de filtração.\n"
            "2. Não desligar máquina (falta de redundância - **MCB off**).\n"
            "3. Monitorar desgaste de metal branco do mancal via laboratório diário.\n\n"
            "⚠️ Risco contínuo contra confiabilidade estrutural."
        )
    },
    {
        "pergunta": "Quando será a próxima intervenção estrutural?",
        "resposta": (
            "📅 **Cronograma de Intervenção FPSO FORTE (PRIO)**\n\n"
            "Atenção prioritária à janela crítica (48-72h) de redundância logística:\n\n"
            "| TAG | Equipamento | Prazo Máximo | Prioridade |\n"
            "|-----|-------------|--------------|------------|\n"
            "| MCA | Compressor HP (Óleo Crítico) | **24-48h** | 🔴 Suporte de Vida |\n"
            "| MCB | Transformadores Auxiliares | **72h** | 🔴 Canibalização MCC |\n"
            "| MCC | Swapping / Realinhamento | 30 dias | 🟡 Baixa |\n\n"
            "Consulte a aba **Sistema de Predição** para acompanhamento da saúde integral."
        )
    },
]

LLM_QA_GERENCIA = [
    {
        "pergunta": "Qual o risco se não instalarmos o sistema de diálise no MCA?",
        "resposta": (
            "💰 **Análise de Risco Financeiro — MCA (Sem Suporte)**\n\n"
            "Não iniciar a diálise de óleo fará com que o número de partículas operacionais continue acima de 12.000 em 4µm e a acidez corroa o mancal de patente. Como o MCB está desativado (falta de trafo), perder o MCA gerará um **Downtime Indesejado Global** no processamento e injeção do sistema FPSO FORTE.\n\n"
            "| Cenário | Probabilidade | Consequência |\n"
            "|---------|--------------|----------------|\n"
            "| Diálise Imediata + Câmbio MCB | Alta (Mitigação) | Ganho de janela operacional |\n"
            "| Trip do MCA sem redundância | 85% | R$ MILHÕES (Queda de Produção) |\n"
            "| Dano catastrófico no eixo (babbitt) | 40% | Troca de rotor/carcaça (+ R$ 9 M) |\n\n"
            "📌 **Recomendação Opex:** Aprovar frete rápido de equipe de diálise offshore."
        )
    },
    {
        "pergunta": "O que devemos fazer para ter redundância o mais rápido possível?",
        "resposta": (
            "📊 **Plano Estratégico (Redundância em FPSO FORTE)**\n\n"
            "A análise atual mostra o **MCA em estado crítico de vibração (91,4 µm) e desgaste**. O **MCC** ainda encontra-se vibrando severamente (95 µm DE) e não pode assumir com segurança total a estabilização da planta contínua.\n\n"
            "🎯 **Ação Gerencial:** Priorize o fornecimento energético do **MCB** com logística reversa dos transformadores originais do MCC (canibalização). A mecânica do MCB consta como estável no PMO histórico."
        )
    },
    {
        "pergunta": "Qual máquina gera maior despesa histórica e risco para o Campo de Frade?",
        "resposta": (
            "⚠️ **Ranking de Concentração Opex - Planta de Gás Natural**\n\n"
            "Focando no complexo de compressão PRIO:\n\n"
            "| # | TAG | Status CAPEX/OPEX | Justificativa de Risco |\n"
            "|---|-----|-------------------|------------------------|\n"
            "| 1 | MCA | 🔴 **Muito Alto** | Máquina base sendo desgastada; se falhar leva a parada total. |\n"
            "| 2 | MCB | 🟡 **Médio (Hardware)** | Parado apenas por questões elétricas (transformadores). |\n"
            "| 3 | MCC | 🟡 **Médio (Projeto)** | Comissionamento frustrado com discrepância de vibração NDE/DE severa. |\n\n"
            "A recomendação definitiva é não aplicar parada de manutenção corretiva no MCA até assegurar que o MCB ou MCC possua capacidade de manobra integral."
        )
    },
    {
        "pergunta": "A máquina nova (MCC) pode suprir a planta neste instante?",
        "resposta": (
            "📉 **Análise de Engenharia — Confiabilidade do MCC**\n\n"
            "Atualmente, embora seja tratada como máquina 'nova', o equipamento demonstrou instabilidade operacional crítica aos 5.200 RPM.\n\n"
            "**Razão do Veto:** O gradiente de diferença no balanço das pontas de eixo é de 4,5x (21 µm NDE para 95 µm DE), apontando para flexão anômala, desalinhamento estrutural acoplado, ou montagem errada dos mancais. Risco alto de contato metal-metal em caso de injeção plena de carga de gás na planta."
        )
    },
    {
        "pergunta": "Gere um resumo executivo da situação atual da planta FPSO FORTE.",
        "resposta": (
            "📋 **Resumo Executivo (Board PRIO) — Complexo Gás Natural**\n"
            f"*Gerado pelo Engine Cognitivo Nautilus em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n"
            "**🔴 Situação: ATENÇÃO OPERACIONAL AGUDA (Risco de Downtime da Produção)**\n\n"
            "A planta compressores atua sustentadas apenas pelo ativo **MCA**, que opera já em descolamento perigoso (>91 µm na carcaça DE e limites críticos de espectrometria Fe/Cu/TAN de lubrificação).\n\n"
            "A não priorização de uma Unidade de Filtragem de Óleo para MCA somada à morosidade no comissionamento de seus backups elétricos (**MCB/MCC**) incorrerá no shut-down generalizado do processamento e exportação.\n\n"
            "**Alerta de Planejamento:** Aprovar imediatamente *swapping* de trafos de MCC -> MCB para obtenção de resiliência e estabilização de contingência de bordo."
        )
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DE PDF FORMATADO (ReportLab)
# ─────────────────────────────────────────────────────────────────────────────
def gerar_pdf_relatorio(df_predicao, df_falhas, custo_total, perfil, username, conversa=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8*cm,
        leftMargin=1.8*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle(
        "TitleNautilus",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#0A2A4E"),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "SubtitleNautilus",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4A6D8C"),
        spaceAfter=2,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "SectionNautilus",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#0A2A4E"),
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "BodyNautilus",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4,
        leading=13,
    )
    footer_style = ParagraphStyle(
        "FooterNautilus",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )

    story = []
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── CABEÇALHO ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("🌊 NAUTILUS — Sistema de Manutenção Preditiva Offshore", title_style))
    story.append(Paragraph("Relatório Técnico Integrado — Gerado Automaticamente pelo Motor Preditivo", subtitle_style))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0A2A4E"), spaceAfter=6))

    # Metadados do relatório
    meta_data = [
        ["Gerado em:", now, "Usuário:", username.title()],
        ["Perfil de Acesso:", perfil.title(), "Versão do Sistema:", "Nautilus v1.0 MVP"],
        ["Plataforma:", "FPSO FORTE — Campo de Frade (PRIO S.A.)", "Classificação:", "INTERNO — USO RESTRITO"],
    ]
    meta_table = Table(meta_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4A6D8C")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#4A6D8C")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCDDEE"), spaceAfter=2))

    # ── SEÇÃO 1: RESUMO EXECUTIVO ──────────────────────────────────────────
    story.append(Paragraph("1. Resumo Executivo da Planta", section_style))

    criticos = len(df_predicao[df_predicao["Status Base"] == "Crítico"])
    atencao = len(df_predicao[df_predicao["Status Base"] == "Atenção"])
    normais = len(df_predicao[df_predicao["Status Base"] == "Normal"])
    total_ativos = len(df_predicao)

    resumo_data = [
        ["Parâmetro", "Valor", "Status"],
        ["Total de Ativos Monitorados", str(total_ativos), "—"],
        ["Ativos em Estado Crítico", str(criticos), "🔴 AÇÃO IMEDIATA"],
        ["Ativos em Estado de Atenção", str(atencao), "🟡 MONITORAR"],
        ["Ativos em Estado Normal", str(normais), "🟢 OK"],
        ["OPEX de Manutenção Acumulado", f"R$ {custo_total:,.2f}", "Controle Financeiro"],
    ]
    resumo_table = Table(resumo_data, colWidths=[8*cm, 4.5*cm, 5.5*cm])
    resumo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2A4E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCDDEE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF4FA")]),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FFEAEA")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFF8E1")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#E8F5E9")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(resumo_table)

    # ── SEÇÃO 2: ALERTAS PREDITIVOS ─────────────────────────────────────
    story.append(Paragraph("2. Alertas Preditivos Integrados — Plano de Manutenção", section_style))
    story.append(Paragraph(
        "Datas e prioridades geradas automaticamente pelo algoritmo preditivo com base em "
        "desvios de vibração e variação térmica detectados pelos sensores dos módulos.",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))

    pred_headers = ["TAG", "Equipamento", "Vibração\n(mm/s)", "Temp.\n(°C)", "Status", "Data Manutenção", "Motivação"]
    pred_data = [pred_headers]
    for _, row in df_predicao.iterrows():
        status_emoji = {"Crítico": "🔴", "Atenção": "🟡", "Normal": "🟢"}.get(row["Status Base"], "")
        pred_data.append([
            row["TAG"],
            Paragraph(row["Equipamento"], ParagraphStyle("cell", fontSize=8, leading=10)),
            f"{row['Vibração']:.1f}",
            f"{row['Temp']:.1f}",
            f"{status_emoji} {row['Status Base']}",
            row["Data Manutenção"],
            Paragraph(row["Motivação"], ParagraphStyle("cell", fontSize=8, leading=10)),
        ])

    pred_table = Table(pred_data, colWidths=[1.5*cm, 4.5*cm, 1.8*cm, 1.6*cm, 2.2*cm, 2.8*cm, 4.6*cm])
    pred_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2A4E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (4, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCDDEE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF4FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(pred_table)

    # ── SEÇÃO 3: HISTÓRICO DE FALHAS ──────────────────────────────────────
    story.append(Paragraph("3. Histórico de Falhas e OPEX de Manutenção", section_style))

    if not df_falhas.empty:
        falhas_headers = ["TAG", "Data", "Tipo de Falha", "Causa Raiz", "Custo (R$)"]
        falhas_data = [falhas_headers]
        for _, row in df_falhas.iterrows():
            falhas_data.append([
                row.get("tag", "—"),
                row.get("data", "—"),
                Paragraph(str(row.get("tipo_falha", "—")), ParagraphStyle("cell", fontSize=8, leading=10)),
                Paragraph(str(row.get("causa_raiz", "—")), ParagraphStyle("cell", fontSize=8, leading=10)),
                f"R$ {row.get('custo_manutencao', 0):,.2f}",
            ])
        # Linha de total
        falhas_data.append(["", "", "", "TOTAL", f"R$ {custo_total:,.2f}"])

        falhas_table = Table(falhas_data, colWidths=[1.8*cm, 2.2*cm, 5*cm, 5.5*cm, 3.5*cm])
        falhas_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2A4E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCDDEE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#EEF4FA")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#0A2A4E")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
            ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(falhas_table)
    else:
        story.append(Paragraph("Nenhum histórico de falha registrado.", body_style))

    # ── SEÇÃO 4: CONSULTAS AO ASSISTENTE (se houver) ─────────────────────
    if conversa and len(conversa) > 0:
        story.append(Paragraph("4. Log de Consultas ao Assistente LLM Nautilus", section_style))
        story.append(Paragraph(
            "Registro das interações realizadas com o assistente de inteligência artificial "
            "durante esta sessão de trabalho.",
            body_style
        ))
        story.append(Spacer(1, 0.2*cm))

        for i, item in enumerate(conversa, 1):
            q_style = ParagraphStyle(
                "Q", fontSize=9, textColor=colors.HexColor("#0A2A4E"),
                fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2
            )
            a_style = ParagraphStyle(
                "A", fontSize=8.5, textColor=colors.HexColor("#222222"),
                leftIndent=14, leading=13, spaceAfter=4
            )
            # Limpar markdown básico para o PDF
            resposta_limpa = item["resposta"]
            for char in ["**", "*", "🔧", "🚨", "🛑", "💰", "📊", "⚠️", "📈", "📋", "🔍", "📌", "💡", "📅"]:
                resposta_limpa = resposta_limpa.replace(char, "")
            # Remover tabelas markdown
            linhas = [l for l in resposta_limpa.split("\n") if not l.strip().startswith("|")]
            resposta_limpa = "\n".join(linhas)

            story.append(Paragraph(f"Consulta {i}: {item['pergunta']}", q_style))
            story.append(Paragraph(resposta_limpa.replace("\n", "<br/>"), a_style))
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#CCDDEE")))

    # ── RODAPÉ ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0A2A4E"), spaceBefore=4))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Documento gerado automaticamente pelo Sistema Nautilus v1.0 MVP em {now}. "
        "Classificação: INTERNO — USO RESTRITO. Não distribuir externamente sem autorização.",
        footer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS tb_ativos")
    c.execute("DROP TABLE IF EXISTS tb_sensores")
    c.execute("DROP TABLE IF EXISTS tb_historico_falhas")
    c.execute("DROP TABLE IF EXISTS inspecoes")

    c.execute('''CREATE TABLE IF NOT EXISTS inspecoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tag_equipamento TEXT, tipo_falha TEXT,
            criticidade TEXT, operador TEXT, data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tb_ativos (id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT, tipo TEXT, data_instalacao TEXT, localizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tb_sensores (id_ativo INTEGER,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vibracao REAL, temperatura REAL, pressao REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tb_historico_falhas (id_ativo INTEGER,
            data TEXT, tipo_falha TEXT, causa_raiz TEXT, custo_manutencao REAL)''')

    c.execute("INSERT OR REPLACE INTO usuarios VALUES ('operador', '1234', 'operacao')")
    c.execute("INSERT OR REPLACE INTO usuarios VALUES ('engenheiro', '1234', 'engenharia')")
    c.execute("INSERT OR REPLACE INTO usuarios VALUES ('gerente', '1234', 'gerencia')")

    c.execute("SELECT COUNT(*) FROM tb_ativos")
    if c.fetchone()[0] == 0:
        ativos = [
            ("MCA", "Compressor de Gás Natural A", "2015-01-10", "Módulo de Compressão HP"),
            ("MCB", "Compressor de Gás Natural B", "2015-01-10", "Módulo de Compressão HP"),
            ("MCC", "Compressor de Gás Natural C", "2024-03-20", "Novo Deck - Comissionamento"),
            ("SEP-F01", "Separador de Fase Líquido/Gás", "2016-06-15", "Módulo de Processo Central"),
            ("VLV-GAS-01", "Válvula de Controle Gás Export.", "2017-09-22", "Manifold de Saída de Gás"),
        ]
        c.executemany("INSERT INTO tb_ativos (tag, tipo, data_instalacao, localizacao) VALUES (?,?,?,?)", ativos)

        sensores = [
            (1, 9.1, 98.0, 120.0),
            (2, 0.0, 25.0, 0.0),
            (3, 9.5, 75.0, 80.0),
            (4, 1.2, 62.0, 42.0),
            (5, 0.3, 38.0, 95.0),
        ]
        c.executemany("INSERT INTO tb_sensores (id_ativo, vibracao, temperatura, pressao) VALUES (?,?,?,?)", sensores)

        falhas = [
            (1, "2026-03-12", "Acidez Extrema do Óleo (TAN 0.67)", "Contaminação Contínua/Falta de Diálise", 350000.00),
            (2, "2025-11-20", "Falha em Transformadores", "Queima Acidental / Fadiga Elétrica", 520000.00),
            (3, "2026-04-01", "Desbalanceamento Severo DE", "Problemas de Alinhamento / Fabricação NDE vs DE", 150000.00),
            (4, "2025-08-14", "Incrustação Parcial no Vaso", "Depósito de Parafina / Falta de Inibe Inorganic.", 48000.00),
        ]
        c.executemany("INSERT INTO tb_historico_falhas VALUES (?,?,?,?,?)", falhas)

        inspecoes = [
            ("MCA",       "Desgaste acelerado patente babbitt",   "CRÍTICA", "Op. Carlos M."),
            ("MCB",       "Ausência contínua de trafos funcionais","ALTA",    "Op. Fátima R."),
            ("MCC",       "Vibração 95µm na rampa a 5.200 RPM",  "MÉDIA",   "Eng. Paulo S."),
            ("SEP-F01",   "Depósito de parafina na entrada",       "MÉDIA",   "Op. Carlos M."),
            ("VLV-GAS-01","Atuador com folga em 40%",              "BAIXA",   "Painel SCADA"),
        ]
        c.executemany("INSERT INTO inspecoes (tag_equipamento, tipo_falha, criticidade, operador) VALUES (?,?,?,?)", inspecoes)

    conn.commit()
    conn.close()


def calcular_preditiva(vibracao, temperatura, tipo_equipamento):
    hoje = datetime.now()
    if vibracao > 7.0 or temperatura > 100.0:
        dias = 2
        itens = "Kit Reparo (Selo/Rolamento)" if vibracao > 7.0 else "Fluidos Químicos de Limpeza/Gaxetas Internas"
        status = "Crítico"
        motivacao = "desvio de leitura de vibração nas 3 últimas verificações" if vibracao > 7.0 else "desvio térmico severo detectado na carcaça"
    elif vibracao > 4.5 or temperatura > 80.0:
        dias = 15
        itens = "Kit Análise Específica Vibração/Lubrificante Especial"
        status = "Atenção"
        motivacao = "elevação contínua no delta térmico do ativo" if temperatura > 80.0 else "alarme intermitente de vibração ativado"
    else:
        dias = 50
        itens = "Plano Preventivo / Inspeção Visual de Rotina"
        status = "Normal"
        motivacao = "ciclo de calibração base pendente neste bimestre"

    data_futura = (hoje + timedelta(days=dias)).strftime("%d/%m/%Y")
    return data_futura, itens, status, dias, motivacao


def get_base_data_com_predicao():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('''
        SELECT a.tag as 'TAG', a.tipo as 'Equipamento',
               s.vibracao as 'Vibração', s.temperatura as 'Temp', s.pressao as 'Pressão'
        FROM tb_sensores s JOIN tb_ativos a ON s.id_ativo = a.id
    ''', conn)
    conn.close()
    df[['Data Manutenção', 'Itens Necessários', 'Status Base', 'Dias Restantes', 'Motivação']] = df.apply(
        lambda row: pd.Series(calcular_preditiva(row['Vibração'], row['Temp'], row['Equipamento'])), axis=1
    )
    df = df.sort_values(by='Dias Restantes').reset_index(drop=True)
    return df


def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT perfil FROM usuarios WHERE usuario=? AND senha=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTE ASSISTENTE LLM REUTILIZÁVEL
# ─────────────────────────────────────────────────────────────────────────────
def render_assistente_llm(qa_list, perfil_key, titulo, descricao, placeholder):
    """Renderiza o componente completo do Assistente LLM com perguntas exemplo e histórico."""
    st.subheader(f"🤖 {titulo}")
    st.markdown(descricao)
    st.markdown("---")

    # Inicializar histórico de conversa na sessão
    hist_key = f"historico_llm_{perfil_key}"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    # ── Perguntas de Exemplo ──────────────────────────────────────────────
    st.markdown("#### 💡 Perguntas Frequentes — Clique para consultar:")

    cols = st.columns(3)
    for i, qa in enumerate(qa_list):
        col = cols[i % 3]
        with col:
            btn_label = qa["pergunta"]
            if len(btn_label) > 55:
                btn_label = btn_label[:52] + "..."
            if st.button(f"❓ {btn_label}", key=f"btn_qa_{perfil_key}_{i}", use_container_width=True):
                st.session_state[hist_key].append({
                    "pergunta": qa["pergunta"],
                    "resposta": qa["resposta"]
                })
                st.session_state[f"chat_input_{perfil_key}"] = ""

    st.markdown("---")

    # ── Input Manual ──────────────────────────────────────────────────────
    st.markdown("#### ✏️ Ou faça sua própria pergunta:")
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        chat_msg = st.text_input(
            "Consulta ao Nautilus LLM",
            placeholder=placeholder,
            key=f"chat_input_{perfil_key}",
            label_visibility="collapsed"
        )
    with col_btn:
        enviar = st.button("Enviar →", key=f"btn_enviar_{perfil_key}", use_container_width=True)

    if enviar and chat_msg:
        msg_lower = chat_msg.lower()

        # ── Dicionário de respostas genéricas por TAG/equipamento ──────────────
        RESPOSTAS_EQUIPAMENTOS = {
            "mca": (
                "🔍 **Nautilus LLM — MCA (Compressor de Gás Natural A)**\n\n"
                "O **MCA** é o compressor primário de gás do Módulo HP do FPSO FORTE (PRIO S.A.), "
                "instalado em 2015. Atualmente opera em **estado crítico**:\n\n"
                "- Vibração axial DE: **91,4 µm** (limite são: ~50 µm)\n"
                "- TAN (óleo): **0,67** — Classe Crítica de Contaminação\n"
                "- Contagem de partículas (óleo 4µm): >12.900 u/mL\n\n"
                "**Risco imediato**: Falha do mancal de patente (babbitt). Sem o MCB ou MCC operando, "
                "um trip aqui paralisa toda a compressão de gás da plataforma.\n\n"
                "⚠️ **Ação recomendada**: Instalar unidade de diálise móvel urgente + monitoramento diário de espectrometria."
            ),
            "mcb": (
                "🔍 **Nautilus LLM — MCB (Compressor de Gás Natural B)**\n\n"
                "O **MCB** encontra-se **indisponível** por falha elétrica nos transformadores de alimentação, "
                "ocorrida em novembro/2025 (custo: R$ 520.000). A estrutura mecânica e o rotor "
                "estão intactos, sem histórico de vibração ou desgaste.\n\n"
                "**Plano de Retomada**: Utilizar os transformadores do MCC (canibalização reversível) "
                "para restabelecer o MCB como backup do MCA enquanto o MCC finaliza o comissionamento.\n\n"
                "📌 Previsão logística de retomada: **72 horas** após aprovação da PTW elétrica."
            ),
            "mcc": (
                "🔍 **Nautilus LLM — MCC (Compressor de Gás Natural C — Novo)**\n\n"
                "O **MCC** é o compressor mais recente (instalação: março/2024), atualmente em fase de "
                "comissionamento. Atingiu 5.200 RPM na rampa de teste, porém apresentou vibração **assêmétrica crítica**:\n\n"
                "- Mancal NDE: 21 µm ✔️\n"
                "- Mancal DE: **95 µm** ❌ (diferença 4,5x)\n\n"
                "**Diagnóstico provável**: Desalinhamento estrutural acoplado ou montagem incorreta dos mancais.\n"
                "Não autorizado para injetar carga de produção até correspôndente alinhamento a laser e rebalanceamento.\n\n"
                "📅 Prazo estimado de liberação: **30 dias** após intervenção de engenharia."
            ),
            "sep-f01": (
                "🔍 **Nautilus LLM — SEP-F01 (Separador de Fase Líq./Gás)**\n\n"
                "O **SEP-F01** opera no Módulo de Processo Central e separa as fases líquida e gasosa "
                "antes do envio ao sistema de export. Parece estar em operação normal:\n\n"
                "- Vibração: 1,2 mm/s ✔️\n"
                "- Temperatura: 62°C ✔️\n"
                "- Pressão: 42 bar ✔️\n\n"
                "**Ocorrência recente**: depósito de parafina detectado na entrada do vaso (ago/2025, "
                "R$ 48.000 de manutenção). Recomendável monitorar periodicidade de aplicação de inibidor inorgânico.\n\n"
                "📅 Próxima inspecão preventiva prevista: **50 dias**."
            ),
            "vlv-gas-01": (
                "🔍 **Nautilus LLM — VLV-GAS-01 (Válvula de Controle Gás Export.)**\n\n"
                "A **VLV-GAS-01** está localizada no Manifold de Saída de Gás (popa). Opera em "
                "condições próximas ao normal, porém o último check via **Painel SCADA** registrou "
                "folga de 40% no atuador (tolerância máxima aceitável: 25%).\n\n"
                "- Vibração: 0,3 mm/s ✔️\n"
                "- Temperatura: 38°C ✔️\n\n"
                "**Ação sugerida**: Verificar curso físico do atuador na próxima janela de inspeção. "
                "Sem risco imediato, mas com potencial de piora em caso de sobrepressão no manifold.\n\n"
                "📅 Prazo preventivo: **50 dias**."
            ),
            "sep": "sep-f01",   # alias
            "valv": "vlv-gas-01",
            "válvula": "vlv-gas-01",
            "separador": "sep-f01",
            "compressor": (
                "📊 **Nautilus LLM — Visão Geral dos Compressores**\n\n"
                "| TAG | Status | Vibração | Observação |\n"
                "|-----|--------|-----------|------------|\n"
                "| MCA | 🔴 Crítico | 91,4 µm | Óleo degradado, sem backup ativo |\n"
                "| MCB | ⚫ Indisponível | 0 µm | Aguardando trafo elétrico |\n"
                "| MCC | 🟡 Atenção | 95 µm | Em comissionamento, NDE/DE assímétrico |\n\n"
                "Para detalhes de um compressor específico, mencione o TAG: **MCA**, **MCB** ou **MCC**."
            ),
        }

        # ── Busca por TAG/palavra-chave nos equipamentos ────────────────────────
        resposta = None
        for tag_key, resp in RESPOSTAS_EQUIPAMENTOS.items():
            if tag_key in msg_lower:
                # resolve aliases
                if isinstance(resp, str) and resp in RESPOSTAS_EQUIPAMENTOS:
                    resposta = RESPOSTAS_EQUIPAMENTOS[resp]
                else:
                    resposta = resp
                break

        # Busca nas perguntas mapeadas (QA list)
        if not resposta:
            for qa in qa_list:
                if any(kw.lower() in msg_lower for kw in qa["pergunta"].split()[:4]):
                    resposta = qa["resposta"]
                    break

        # Resposta genérica de fallback
        if not resposta:
            resposta = (
                f"🔍 **Nautilus LLM — Análise Processada**\n\n"
                f"Sua consulta *\"{chat_msg}\"* foi recebida e indexada contra a base vetorial local.\n\n"
                "Equipamentos disponíveis para consulta: **MCA**, **MCB**, **MCC**, **SEP-F01**, **VLV-GAS-01**.\n"
                "Você também pode perguntar sobre: vibração, temperatura, óleo, transformador, comissionamento, "
                "diálise, parada de emergência ou manutenção preventiva.\n\n"
                "📌 Para suporte avançado, acione o engenheiro de confiabilidade de plantão."
            )

        st.session_state[hist_key].append({"pergunta": chat_msg, "resposta": resposta})
        st.rerun()

    # ── Histórico de Conversa ──────────────────────────────────────────────
    if st.session_state[hist_key]:
        st.markdown("---")
        st.markdown("#### 📜 Histórico da Sessão")

        # Botão limpar histórico
        col_h1, col_h2 = st.columns([4, 1])
        with col_h2:
            if st.button("🗑️ Limpar", key=f"limpar_{perfil_key}", use_container_width=True):
                st.session_state[hist_key] = []
                st.rerun()

        for i, item in enumerate(reversed(st.session_state[hist_key])):
            with st.expander(f"❓ {item['pergunta']}", expanded=(i == 0)):
                st.markdown(item["resposta"])

    return hist_key  # retorna chave do histórico para uso no PDF


# ─────────────────────────────────────────────────────────────────────────────
# SEÇÃO DE GERAÇÃO DE PDF (componente reutilizável)
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# FPSO 3D — carregamento do modelo FBX (via conversão OBJ)
# ─────────────────────────────────────────────────────────────────────────────
OBJ_PATH = "FPSO_converted_from_FBX.obj"

@st.cache_data(show_spinner="Carregando malha do modelo 3D (Importado de FBX)…")
def _load_fpso_mesh():
    """Carrega o OBJ diretamente (22k faces)."""
    import trimesh
    raw = trimesh.load(OBJ_PATH, force="mesh")
    verts  = np.array(raw.vertices, dtype=float)
    faces  = np.array(raw.faces,    dtype=int)
    bounds = np.array(raw.bounding_box.bounds, dtype=float)
    return verts, faces, bounds

def _line(xs, ys, zs, color='#AAAAAA', w=3):
    return go.Scatter3d(
        x=xs, y=ys, z=zs, mode='lines',
        line=dict(color=color, width=w),
        hoverinfo='skip', showlegend=False
    )

def create_fpso_plot():
    """
    Gera figura Plotly 3D usando o modelo OBJ real do FPSO Jotun A.
    Mantém todos os marcadores RFID dos ativos PRIO.
    """
    T = []

    # ── Carrega malha real ────────────────────────────────────────────────────
    verts, faces, bounds = _load_fpso_mesh()
    bmin, bmax = bounds[0], bounds[1]
    ext   = bmax - bmin                    # extensões (X,Y,Z)
    ctr   = (bmin + bmax) / 2             # centro geométrico

    # O arquivo FBX tem seu comprimento principal ao longo do eixo Z
    deck_y  = bmin[1] + ext[1] * 0.38  # Trazendo a base para muito mais perto da chaparia do casco real
    bow_z   = bmax[2]      # proa está no extremo Z
    stern_z = bmin[2]      # popa
    mid_z   = ctr[2]       # meio longitudinal
    mid_x   = ctr[0]       # meio lateral (largura em X)

    # ── Oceano ────────────────────────────────────────────────────────────────
    margin_x = max(ext[0], ext[2]) * 0.55
    margin_z = max(ext[0], ext[2]) * 0.55
    xi = np.linspace(bmin[0]-margin_x, bmax[0]+margin_x, 30)
    zi = np.linspace(bmin[2]-margin_z, bmax[2]+margin_z, 30)
    Xo, Zo = np.meshgrid(xi, zi)
    waterline_y = bmin[1] + ext[1] * 0.12 # Água a 12% da altura da quilha
    T.append(go.Surface(
        x=Xo, y=np.full_like(Xo, waterline_y), z=Zo,
        colorscale=[[0,'#030C18'],[0.5,'#062240'],[1,'#0A3560']],
        showscale=False, opacity=0.72, hoverinfo='skip',
    ))

    # ── Modelo FPSO (Convertido de FBX) ───────────────────────────────────────
    T.append(go.Mesh3d(
        x=verts[:,0], y=verts[:,1], z=verts[:,2],
        i=faces[:,0],  j=faces[:,1],  k=faces[:,2],
        color='#9EAEB8', # Cor sólida (cinza naval) opaca, como solicitado
        opacity=1.0,     # Totalmente opaco
        flatshading=True,
        lighting=dict(
            ambient=0.4,
            diffuse=0.9,
            roughness=0.9,
            specular=0.2,
            fresnel=0.5,
        ),
        lightposition=dict(x=mid_x*1.5, y=bmax[1]*2, z=bow_z*1.5),
        name='FPSO FBX',
        showscale=False,
        hoverinfo='skip',  # Desabilita seleção/hover na geometria
        showlegend=True,
    ))

    # ── Marcadores RFID ───────────────────────────────────────────────────────
    # Z = comprimento (proa→popa)
    # Y = altura
    # X = largura
    above = ext[1] * 0.005
    # Posição base do módulo de compressão HP — zona central do convés
    mod_z = bow_z - ext[2] * 0.10   # ~10% a partir da proa (zona da proa do navio)
    mod_y = deck_y + ext[1] * 0.05  # elevação baixa, próximo ao deck
    gap_x = ext[0] * 0.06           # espaçamento lateral pequeno (mesmo módulo)

    RFID = [
        dict(tag='MCA', nome='Compressor de Gás Natural A', local='Módulo HP',
             status='🔴 Crítico', color='#FF4444',
             vib='91,4 µm ⚠️', temp='98°C ⚠️', man='Urgente (Sem Suporte de Óleo)',
             z=mod_z, y=mod_y, x=mid_x - gap_x),
        dict(tag='MCB', nome='Compressor de Gás Natural B', local='Módulo HP',
             status='⚫ Indisponível', color='#888888',
             vib='0,0 µm', temp='25°C', man='Aguardando Trafo',
             z=mod_z, y=mod_y, x=mid_x),
        dict(tag='MCC', nome='Compressor de Gás Natural C (Novo)', local='Módulo HP',
             status='🟡 Atenção', color='#FFDD44',
             vib='95,0 µm ⚠️', temp='75°C', man='Re-alinhamento (30 dias)',
             z=mod_z, y=mod_y, x=mid_x + gap_x),
        # Equipamentos de apoio — distribuídos ao longo do convés
        dict(tag='SEP-F01', nome='Separador de Fase Líq./Gás', local='Módulo de Processo Central',
             status='🟢 Normal', color='#44DD88',
             vib='1,2 mm/s', temp='62°C', man='em 50 dias',
             z=mid_z, y=deck_y + ext[1]*0.05, x=mid_x - ext[0]*0.05),
        dict(tag='VLV-GAS-01', nome='Válvula Controle Gás Export.', local='Manifold Saída de Gás',
             status='🟢 Normal', color='#44DD88',
             vib='0,3 mm/s', temp='38°C', man='em 50 dias',
             z=stern_z + ext[2]*0.20, y=deck_y + ext[1]*0.04, x=mid_x),
    ]

    ex = [e['x']     for e in RFID]
    ey = [e['y']     for e in RFID]
    ez = [e['z']     for e in RFID]
    ec = [e['color'] for e in RFID]
    ht = [
        f"<b>📡 {e['tag']}</b><br>"
        f"<i>{e['nome']}</i><br>"
        f"─────────────────<br>"
        f"📍 {e['local']}<br>"
        f"🔘 Status: {e['status']}<br>"
        f"〜 Vibração: {e['vib']}<br>"
        f"🌡 Temperatura: {e['temp']}<br>"
        f"⏱ Próx. Manutenção: {e['man']}"
        for e in RFID
    ]

    # Linhas de antena (do deck até o marcador)
    for e in RFID:
        T.append(_line(
            [e['x'], e['x']], [e['y']-above*0.9, e['y']], [e['z'], e['z']],
            color=e['color'], w=1.5
        ))

    # Halos externos (efeito glow)
    T.append(go.Scatter3d(
        x=ex, y=ey, z=ez, mode='markers',
        marker=dict(size=38, color=ec, opacity=0.10),
        hoverinfo='skip', showlegend=False,
    ))
    T.append(go.Scatter3d(
        x=ex, y=ey, z=ez, mode='markers',
        marker=dict(size=28, color=ec, opacity=0.20),
        hoverinfo='skip', showlegend=False,
    ))
    # Esfera principal + label + hover
    T.append(go.Scatter3d(
        x=ex, y=ey, z=ez,
        mode='markers+text',
        marker=dict(
            size=16, color=ec,
            line=dict(color='white', width=2),
            symbol='circle',
        ),
        text=[e['tag'] for e in RFID],
        textposition='top center',
        textfont=dict(size=10, color='white', family='monospace'),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=ht,
        name='Pontos RFID Nautilus',
        showlegend=True,
    ))

    # ── Layout ────────────────────────────────────────────────────────────────
    fig = go.Figure(data=T)
    fig.update_layout(
        paper_bgcolor='#040d1a',
        margin=dict(l=0, r=0, t=30, b=0),
        title=dict(
            text='FPSO Jotun A · Campo de Frade · PRIO S.A.',
            font=dict(color='#4dc3ff', size=13),
            x=0.5, xanchor='center',
        ),
        legend=dict(
            x=0.01, y=0.98,
            bgcolor='rgba(4,13,26,0.85)',
            bordercolor='rgba(77,195,255,0.3)',
            borderwidth=1,
            font=dict(color='white', size=10),
        ),
        scene=dict(
            bgcolor='#040d1a',
            xaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            zaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            camera=dict(
                up=dict(x=0, y=1, z=0),
                eye=dict(x=0.0, y=0.6, z=2.2),
                center=dict(x=0, y=-0.15, z=0),
            ),
            aspectmode='data',
        ),
        height=620,
    )
    return fig

def render_tab_fpso():
    """Renderiza a aba do mapa 3D FPSO com Plotly (funciona offline)."""
    st.subheader("🛢️ Mapa 3D FPSO — Monitoramento RFID · PRIO S.A.")
    st.markdown(
        "Modelo tridimensional real da embarcação operada pela **PRIO S.A.** "
        "Os marcadores pulsantes indicam os pontos de monitoramento RFID integrados ao Nautilus. "
        "**Passe o mouse** nos marcadores para ver os dados do ativo em tempo real."
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("🔴 Ativos Críticos", "1", delta="MCA", delta_color="inverse")
    with col_b:
        st.metric("🟡 Indisponíveis/Atenção", "2", delta="MCB · MCC", delta_color="off")
    with col_c:
        st.metric("📡 Pontos RFID Ativos", "3 / 3", delta="100% cobertura")

    st.markdown("---")
    fig = create_fpso_plot()
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['toImage'],
        'displaylogo': False,
    })
    st.markdown("---")
    st.markdown(
        "💡 **Legenda:** Marcadores **vermelhos** = ativos críticos com intervenção urgente (≤ 2 dias). "
        "Marcadores **verdes** = dentro do envelope operacional normal. "
        "Use o mouse para rotacionar, zoom e inspecionar a plataforma."
    )


def render_secao_pdf(df_predicao, df_falhas, custo_total, perfil, username, hist_key):
    st.markdown("---")
    st.subheader("📄 Geração de Relatório PDF")
    st.markdown(
        "Gere um relatório técnico completo e formatado com os dados atuais do sistema, "
        "incluindo alertas preditivos, histórico de falhas e log de consultas ao assistente."
    )

    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        incluir_preditivo = st.checkbox("✅ Alertas Preditivos", value=True, key=f"pdf_pred_{perfil}")
    with col_opt2:
        incluir_falhas = st.checkbox("✅ Histórico de Falhas", value=True, key=f"pdf_falhas_{perfil}")
    with col_opt3:
        incluir_llm = st.checkbox("✅ Log do Assistente LLM", value=True, key=f"pdf_llm_{perfil}")

    if st.button("🖨️ Gerar Relatório PDF Completo", key=f"gerar_pdf_{perfil}", use_container_width=True, type="primary"):
        with st.spinner("Compilando relatório... aguarde."):
            conversa = st.session_state.get(hist_key, []) if incluir_llm else []
            df_f = df_falhas if incluir_falhas else pd.DataFrame()
            df_p = df_predicao if incluir_preditivo else pd.DataFrame(columns=df_predicao.columns)

            pdf_buffer = gerar_pdf_relatorio(
                df_p, df_f, custo_total, perfil, username, conversa
            )
            nome_arquivo = f"Nautilus_Relatorio_{perfil}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        st.success("✅ Relatório gerado com sucesso!")
        st.download_button(
            label="⬇️ Baixar Relatório PDF",
            data=pdf_buffer,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "perfil": "", "username": ""})

    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            logo_path = "logo nova_transparent.png"
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as image_file:
                    enc = base64.b64encode(image_file.read()).decode()
                st.markdown(
                    f"<div style='text-align: center;'><img src='data:image/png;base64,{enc}' width='550'/></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<h2 style='text-align:center;'>Nautilus</h2>", unsafe_allow_html=True)

            st.markdown("<h1 style='text-align: center; padding-bottom: 20px;'>Login - Nautilus</h1>", unsafe_allow_html=True)
            st.info("""**Credenciais de Acesso (Teste):**
- **Operação:** `operador`
- **Engenharia:** `engenheiro`
- **Gerência:** `gerente`

**Senha Padrão:** `1234`""")
            with st.form("login_form"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                    perfil = login_user(username, password)
                    if perfil:
                        st.session_state.update({"logged_in": True, "perfil": perfil, "username": username})
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
        return

    perfil = st.session_state["perfil"]
    username = st.session_state["username"]
    roles_map = {"operacao": "Operação", "engenharia": "Engenharia", "gerencia": "Gerência"}

    st.sidebar.title(f"Olá, {username.title()}")
    st.sidebar.markdown(f"**Perfil:** {roles_map.get(perfil)}")
    st.sidebar.markdown("---")

    if perfil == "operacao":
        st.sidebar.header("📤 Ingestão PDF (OCR)")
        uploaded_file = st.sidebar.file_uploader("Relatório de Campo", type="pdf")
        if uploaded_file is not None:
            st.sidebar.success("Arquivo recebido pelo motor Preditivo (Mock).")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.update({"logged_in": False, "perfil": "", "username": ""})
        st.rerun()

    conn = sqlite3.connect(DB_FILE)
    df_predicao_global = get_base_data_com_predicao()
    df_falhas_global = pd.read_sql_query(
        "SELECT a.tag, f.data, f.tipo_falha, f.causa_raiz, f.custo_manutencao "
        "FROM tb_historico_falhas f JOIN tb_ativos a ON f.id_ativo = a.id", conn
    )
    custo_total = pd.read_sql_query(
        "SELECT COALESCE(SUM(custo_manutencao), 0) as total FROM tb_historico_falhas", conn
    ).iloc[0]["total"]

    # ── PERFIL: OPERAÇÃO ──────────────────────────────────────────────────
    if perfil == "operacao":
        st.title("🛠️ Portal - Operação de Produção")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Leitura de Equipamento",
            "Sistema de Predição à Manutenção",
            "Consulta RFID",
            "💬 Assistente LLM (Nautilus)",
            "🗺️ Modelo 3D FPSO",
            "📈 Simulador Preditivo",
        ])

        with tab1:
            df_inspecoes = pd.read_sql_query(
                "SELECT tag_equipamento AS 'TAG', tipo_falha AS 'Ocorrência', "
                "criticidade AS 'Criticidade', operador AS 'Operador/Dispositivo', "
                "data_upload AS 'Data' FROM inspecoes",
                conn
            )
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.subheader("⚠️ Últimas Inspeções de Campo")
                st.dataframe(df_inspecoes.head(10), use_container_width=True)
            with c2:
                st.subheader("Balanço de Criticidades (%)")
                if not df_inspecoes.empty:
                    df_crit = df_inspecoes['Criticidade'].value_counts(normalize=True).reset_index()
                    df_crit.columns = ['Criticidade', 'Representatividade %']
                    df_crit['Representatividade %'] = df_crit['Representatividade %'] * 100
                    st.bar_chart(df_crit.set_index('Criticidade'))

        with tab2:
            st.subheader("🤖 Alertas Preditivos Integrados")
            st.markdown("Datas geradas autônomamente com base em desvios de vibração e variação térmica registrados nos módulos.")
            df_view = df_predicao_global[['TAG', 'Equipamento', 'Data Manutenção', 'Motivação', 'Itens Necessários', 'Status Base']]
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            st.markdown("---")
            st.subheader("Mapeamento Saudável da Planta (%)")
            df_status_perc = df_predicao_global['Status Base'].value_counts(normalize=True).reset_index()
            df_status_perc.columns = ['Status Base', 'Porcentagem (%)']
            df_status_perc['Porcentagem (%)'] = df_status_perc['Porcentagem (%)'] * 100
            st.bar_chart(df_status_perc.set_index('Status Base'))

        with tab3:
            st.subheader("📡 Leitor de Campo (Integração RFID)")
            rfid_input = st.text_input("Código Físico (RFID):", placeholder="TAG-XXX-999")
            if st.button("Buscar Equipamento", use_container_width=True):
                if rfid_input:
                    st.success(f"Conectado à Base de Conhecimento Segura de {rfid_input.upper()}")
                    x1, x2 = st.columns(2)
                    with x1:
                        st.markdown(f"**TAG Associado:** {rfid_input.upper()}")
                        st.download_button("Baixar Diagrama P&ID (PDF)", "mock", file_name=f"{rfid_input}_PID.pdf")
                    with x2:
                        st.markdown("**Checklist Virtual Concluído (%)**")
                        df_mock_rfid = pd.DataFrame({"Tarefas Executadas": ["Feitas", "Pendentes"], "Progresso %": [85, 15]})
                        st.bar_chart(df_mock_rfid.set_index("Tarefas Executadas"))
                else:
                    st.warning("Aproxime o sensor de campo ou digite o registro de patrimônio.")

        with tab4:
            hist_key_op = render_assistente_llm(
                qa_list=LLM_QA_OPERACAO,
                perfil_key="operacao",
                titulo="Assistente de Bordo (IA Generativa — Operação)",
                descricao="Consulte procedimentos operacionais, status de equipamentos e orientações técnicas "
                          "conversando com o LLM interno treinado na base de conhecimento offshore da Nautilus.",
                placeholder="Ex: Qual o fluxo de bloqueio da válvula VAL-01?",
            )
            render_secao_pdf(df_predicao_global, df_falhas_global, custo_total, perfil, username, hist_key_op)

        with tab5:
            render_tab_fpso()

        with tab6:
            st.subheader("📈 Simulador Interativo de Monitoramento Preditivo")
            st.markdown("Painel de exemplo inspirado na saída interativa do assistente de inteligência artificial.")
            
            # CABEÇALHO
            st.markdown("#### Monitoramento Preditivo: Compressor MCA")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.error("🔴 Status Atual: CRÍTICO")
            with col_s2:
                st.metric("Risco de Falha", "85%", delta="+25%", delta_color="inverse")
            with col_s3:
                st.metric("Próxima Preventiva", "Urgente", delta="Perda de Suporte", delta_color="off")
            
            # ALERT BOX
            st.warning("⚠️ **Operação Assêmica:** Equipamento vibrando fora do delta seguro (91,4 µm). Necessário avaliar plano logístico ou acoplamento a gerador portátil imediatamente.")
            
            # GRAFICO
            st.markdown("#### Tendência de Operação (Últimos 7 Dias)")
            dias = [f"Dia {i}" for i in range(1, 8)]
            fig_sim = sp.make_subplots(specs=[[{"secondary_y": True}]])
            fig_sim.add_trace(go.Scatter(x=dias, y=[95, 96, 95, 96, 97, 98, 98], name="Temperatura Mancal (°C)", line=dict(color="#FF4444", width=3)), secondary_y=False)
            fig_sim.add_trace(go.Scatter(x=dias, y=[45.0, 50.0, 62.0, 75.0, 80.0, 88.0, 91.4], name="Vibração Axial (µm)", line=dict(color="#FFDD44", width=3, dash='dash')), secondary_y=True)
            fig_sim.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_sim.update_yaxes(title_text="Temperatura (°C)", secondary_y=False, gridcolor="rgba(255,255,255,0.1)")
            fig_sim.update_yaxes(title_text="Vibração (µm)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_sim, use_container_width=True, config={'displayModeBar': False})

            # HISTORICO
            st.markdown("#### Histórico de Padrões de Falha")
            historico_sim = pd.DataFrame([
                {"Data": "15/03/2026", "Evento Detectado": "Vibração 91 µm Elevada", "Causa Raiz": "Desalinhamento/Acidez Óleo", "Ação Corretiva": "Solicitação de Diálise"},
                {"Data": "10/02/2026", "Evento Detectado": "Elevação Térmica", "Causa Raiz": "Atrito em Patente Fe/Cu", "Ação Corretiva": "Monitoramento Semanal"},
            ])
            st.dataframe(historico_sim, use_container_width=True, hide_index=True)

    # ── PERFIL: ENGENHARIA ─────────────────────────────────────────────────
    elif perfil == "engenharia":
        st.title("🔬 Portal - Engenharia de Confiabilidade")

        tab_e1, tab_e2 = st.tabs(["Telemetria Contínua (Sensores)", "Métricas de Falhas Avançadas"])

        with tab_e1:
            st.subheader("📡 Dados de Sensores (Live View)")
            st.dataframe(df_predicao_global[['TAG', 'Equipamento', 'Vibração', 'Temp', 'Pressão']], use_container_width=True)
            st.markdown("---")
            st.subheader("Variação de Temperatura Preditiva em Relação ao Limiar Crítico (100°C) (%)")
            df_temp = df_predicao_global.copy()
            df_temp['Carga Térmica Ocupada (%)'] = (df_temp['Temp'] / 100.0) * 100
            st.bar_chart(df_temp[['TAG', 'Carga Térmica Ocupada (%)']].set_index('TAG'))

        with tab_e2:
            st.subheader("🧾 Histórico Causa Raiz Global")
            st.dataframe(df_falhas_global, use_container_width=True)
            if not df_falhas_global.empty:
                st.markdown("---")
                st.subheader("Representatividade de Custos nos Históricos (%)")
                soma = df_falhas_global['custo_manutencao'].sum()
                df_falhas_pct = df_falhas_global.copy()
                df_falhas_pct['Buraco Financeiro %'] = (df_falhas_pct['custo_manutencao'] / soma) * 100
                st.bar_chart(df_falhas_pct[['tag', 'Buraco Financeiro %']].set_index('tag'))

            st.markdown("---")
            st.subheader("📄 Exportar Dados de Confiabilidade (PDF)")
            if st.button("🖨️ Gerar Relatório de Engenharia", use_container_width=True, type="primary", key="pdf_eng"):
                with st.spinner("Compilando relatório técnico..."):
                    pdf_buffer = gerar_pdf_relatorio(
                        df_predicao_global, df_falhas_global, custo_total, perfil, username
                    )
                    nome = f"Nautilus_Engenharia_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.success("✅ Relatório de engenharia gerado!")
                st.download_button("⬇️ Baixar PDF de Confiabilidade", data=pdf_buffer,
                                   file_name=nome, mime="application/pdf", use_container_width=True)

    # ── PERFIL: GERÊNCIA ──────────────────────────────────────────────────
    elif perfil == "gerencia":
        st.title("📊 Portal - Gerência e Planejamento Integrado")

        tab_g1, tab_g2, tab_g3 = st.tabs(["Painel Estratégico", "💬 Assistente LLM (Nautilus)", "🗺️ Modelo 3D FPSO"])

        with tab_g1:
            st.subheader("📅 Paradas Futuras (Preditivas de Manutenção Inteligente)")
            st.markdown("Planejamento Extraído Automaticamente dos Sensores Ativos.")
            df_view_gerente = df_predicao_global[['TAG', 'Equipamento', 'Data Manutenção', 'Motivação', 'Itens Necessários']]
            st.dataframe(df_view_gerente, use_container_width=True, hide_index=True)
            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Custo Manutenção (Acumulado Anual)", f"R$ {custo_total:,.2f}")
                st.info("💡 Como gerente, este controle financeiro garante visibilidade sobre os piores cenários.")
            with c2:
                st.subheader("Distribuição Financeira dos Gastos por Sistema Crítico (%)")
                df_gastos = pd.read_sql_query(
                    "SELECT a.tipo as 'Módulo', f.custo_manutencao as custo "
                    "FROM tb_historico_falhas f JOIN tb_ativos a ON f.id_ativo = a.id", conn
                )
                soma_gasto = df_gastos['custo'].sum()
                df_gastos_agrupado = df_gastos.groupby('Módulo').sum().reset_index()
                df_gastos_agrupado['Impacto Ponderado %'] = (df_gastos_agrupado['custo'] / soma_gasto) * 100
                st.bar_chart(df_gastos_agrupado.set_index('Módulo')[['Impacto Ponderado %']])

            st.markdown("---")
            st.subheader("📤 Distribuição de Plano de Ação")
            email_target = st.text_input("Notificar Stakeholders (E-mail):", placeholder="diretoria@empresa.com.br")
            if st.button("Enviar Relatório Opex/Capex Preditivo", use_container_width=True):
                if email_target:
                    st.success(f"Relatório estratégico enviado com sucesso para {email_target}!")
                else:
                    st.warning("Preencha o e-mail de destino.")

        with tab_g2:
            hist_key_ger = render_assistente_llm(
                qa_list=LLM_QA_GERENCIA,
                perfil_key="gerencia",
                titulo="Agente de Inteligência Gerencial",
                descricao="Consulte cruzamento de dados logísticos, financeiros e de risco "
                          "interagindo em linguagem natural com o LLM interno da Nautilus.",
                placeholder="Ex: Qual o impacto financeiro de postergar a parada do CMP-01?",
            )
            render_secao_pdf(df_predicao_global, df_falhas_global, custo_total, perfil, username, hist_key_ger)

        with tab_g3:
            render_tab_fpso()

    conn.close()


if __name__ == "__main__":
    main()
