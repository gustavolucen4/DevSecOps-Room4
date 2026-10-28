import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (páginas > 1)
        if self._pageNumber > 1:
            self.drawString(36, 805, "TaskFlow — Roteiro de Apresentação | Atividade 2 (DAST, IaC e Observabilidade)")
            self.drawRightString(A4[0] - 36, 805, "Grupo Room 4 · gustavolucen4/DevSecOps-Room4")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 800, A4[0] - 36, 800)

        # Footer
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(A4[0] - 36, 25, page_str)
        self.drawString(36, 25, "Confidencial / Uso Acadêmico — Duração: ~10 min cronometrados")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 35, A4[0] - 36, 35)
        self.restoreState()

def build_pdf(output_paths):
    doc = SimpleDocTemplate(
        output_paths[0],
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Cores
    c_primary = colors.HexColor("#0f172a")     # Slate 900
    c_secondary = colors.HexColor("#1e40af")   # Blue 800
    c_accent = colors.HexColor("#0284c7")      # Sky 600
    c_dark = colors.HexColor("#1e293b")        # Slate 800
    c_muted = colors.HexColor("#475569")       # Slate 600
    c_bg_box = colors.HexColor("#f8fafc")      # Slate 50
    c_border = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_muted,
        spaceAfter=10
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceBefore=8,
        spaceAfter=4
    )

    slide_badge_style = ParagraphStyle(
        'SlideBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=c_primary
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_dark
    )

    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=c_primary
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # Cabeçalho
    story.append(Paragraph("TaskFlow — Roteiro de Apresentação da Atividade 2", title_style))
    story.append(Paragraph("Lab de DAST, IaC e Observabilidade · Duração: ~10 min · Grupo Room 4 · gustavolucen4/DevSecOps-Room4", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_secondary, spaceAfter=8))

    # Tabela de Preparação
    prep_content = [
        [Paragraph("<b>Checklist Pré-Apresentação (5 min antes):</b>", bold_label)],
        [Paragraph("1. Docker Compose rodando no host: <code>docker compose up -d</code> (App em :8080, Grafana em :3000)<br/>"
                   "2. Abas abertas: Home do Repo, PR #2 (Demo DAST), PR #3 (Demo IaC), Grafana Dashboard e Runbook NIST.<br/>"
                   "3. Terminal pronto na raiz para executar: <code>./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25</code>", body_style)]
    ]
    t_prep = Table(prep_content, colWidths=[523])
    t_prep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_prep)
    story.append(Spacer(1, 8))

    # Função para criar cards de blocos
    def create_block_card(time_str, title, speaker, screen, goal, actions, speech):
        header_table = Table([
            [Paragraph(f"<b>{time_str}</b>", slide_badge_style),
             Paragraph(f"<b>{title}</b> — <i>Responsável: {speaker}</i>", slide_title_style)]
        ], colWidths=[80, 443])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), c_secondary),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))

        rows = [
            [header_table],
            [Paragraph(f"<b>Tela / Onde Clicar:</b> {screen}", body_style)],
            [Paragraph(f"<b>Objetivo:</b> {goal}", body_style)],
            [Paragraph(f"<b>Passo a Passo da Ação:</b><br/>{actions}", body_style)],
            [Paragraph(f"<b>Fala Sugerida:</b> <i>\"{speech}\"</i>", body_style)]
        ]

        t_card = Table(rows, colWidths=[523])
        t_card.setStyle(TableStyle([
            ('BACKGROUND', (0,1), (-1,-1), c_bg_box),
            ('BOX', (0,0), (-1,-1), 1, c_border),
            ('PADDING', (0,1), (-1,-1), 5),
            ('LINEBELOW', (0,1), (-1,-2), 0.5, c_border),
        ]))
        return t_card

    # Bloco 1
    story.append(create_block_card(
        "0:00 - 1:30", "Bloco 1: Contexto e Evolução", "Gustavo Lucena",
        "Aba 1 (Home do repositório no GitHub)",
        "Explicar a evolução da esteira estática (Atividade 1) para o ciclo completo em runtime (Atividade 2).",
        "• Mostrar a home do repositório oficial forkado e a branch main.<br/>"
        "• Destacar que o repositório possui 9 Quality Gates ativos exigidos pelo ruleset da main.",
        "Olá a todos. Na Atividade 1 construímos nossa esteira focada em código estático. Na Atividade 2, fechamos o ciclo de DevSecOps: testamos a aplicação em execução com DAST no pipeline (OWASP ZAP), endurecemos a infraestrutura como código (Terraform e Docker Compose) auditada por Checkov e Trivy, e implementamos observabilidade defensiva com logs JSON correlacionados por request_id e runbook NIST SP 800-61."
    ))
    story.append(Spacer(1, 6))

    # Bloco 2
    story.append(create_block_card(
        "1:30 - 4:00", "Bloco 2: Demonstração DAST", "Filipe Almeida / Júlio Santos",
        "Aba 2 (PR #2: Regressão de XSS)",
        "Comprovar que o DAST é um Quality Gate real que bloqueia o merge no GitHub Actions.",
        "1. Abrir o PR #2 que reintroduziu a falha trocando <code>{{ error }}</code> por <code>{{ error | safe }}</code>.<br/>"
        "2. Apontar o check <b>DAST - ZAP Baseline</b> em vermelho e o botão de Merge <b>bloqueado</b>.<br/>"
        "3. Explicar a espera ativa com curl no /login (evita o 'ZAP atacando o nada') e o ZAP Full Scan injetando o payload.<br/>"
        "4. Mostrar a correção na main com autoescape limpo sem | safe em todos os sinks (q e erro).",
        "Para comprovar o gate em ação, criamos o PR #2 simulando uma regressão de XSS no login. O ZAP esperou a app subir, injetou o payload de ataque e reprovou o check na regra 40012 (A03 Injection). A proteção de branch bloqueou o merge. Na main, corrigimos todos os sinks com autoescape Jinja2 e removemos o debug."
    ))
    story.append(Spacer(1, 6))

    # Bloco 3
    story.append(create_block_card(
        "4:00 - 6:00", "Bloco 3: Segurança em IaC", "Frederico Cavalcanti / Pedro Holanda",
        "Aba 3 (PR #3: SSH Aberto) e docker-compose.yml",
        "Demonstrar a auditoria automatizada de infraestrutura bloqueando configurações inseguras.",
        "1. Abrir o PR #3 com a porta 22 (SSH) aberta para <code>0.0.0.0/0</code> no Terraform.<br/>"
        "2. Mostrar o Checkov (CKV_AWS_24) e o Trivy config reprovados, bloqueando o PR.<br/>"
        "3. Apontar no código da main: SG restrito a <code>allowed_cidr</code>, S3 KMS com rotação e logging.<br/>"
        "4. No Compose: 3 redes isoladas, SQLite em volume sem porta no host e Promtail sem docker.sock.",
        "Aqui no PR #3 mostramos o Quality Gate de IaC: ao abrir o SSH para 0.0.0.0/0, o Checkov e o Trivy travaram o merge. Na main corrigida, o SG só aceita nosso IP confiável, o S3 é privado e criptografado com KMS, e no Compose o banco e o Promtail são totalmente isolados sem expor portas."
    ))
    story.append(Spacer(1, 6))

    # Bloco 4
    story.append(create_block_card(
        "6:00 - 8:30", "Bloco 4: Incidente ao Vivo & NIST", "Gustavo Lucena / Filipe Almeida",
        "Terminal + Aba 4 (Grafana) + Aba 5 (Runbook NIST)",
        "Exercitar o ataque simulado, mostrar o disparo no Grafana e percorrer as 4 fases do NIST.",
        "1. Executar no terminal: <code>./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25</code>.<br/>"
        "2. No Grafana: mostrar o pico de falhas e a query de disparo: <code>sum by (client_ip) (count_over_time({job='taskflow', event='login_failed'} | json [5m])) > 10</code>.<br/>"
        "3. No Runbook: percorrer Preparação, Detecção/Análise (query de sucesso vazia = não invadido), Contenção (rate limit Nginx) e Pós-Incidente.<br/>"
        "4. Prova de ouro: busca por 'senha-errada' no Loki retorna 0 linhas (higiene de logs).",
        "Este é o momento mais importante da demo: estou disparando 25 tentativas de login com tokens CSRF reais. No Grafana, vejam o pico subindo. Nosso runbook NIST SP 800-61 entra em ação: checamos que não houve login_success, aplicamos a contenção no Nginx e comprovamos que nenhuma senha vazou no Loki."
    ))
    story.append(Spacer(1, 6))

    # Bloco 5
    story.append(create_block_card(
        "8:30 - 10:00", "Bloco 5: Trade-offs & Conclusão", "Todos os Integrantes",
        "Aba 1 (Rulesets da main e README)",
        "Explicar decisões arquiteturais e responder às perguntas da banca.",
        "<b>1. Ausência de filtro paths: no iac-scan.yml (Prevenção de deadlock em PRs):</b><br/>"
        "• <i>Contexto:</i> O iac-scan.yml provê 3 checks obrigatórios (Required Status Checks) na proteção da main: IaC - Terraform validate, IaC - Checkov e IaC - Trivy config.<br/>"
        "• <i>O Problema:</i> Se configurássemos um filtro como <code>paths: ['infra/**', 'docker-compose*.yml']</code>, um PR que alterasse apenas código de aplicação (ex: <code>app.py</code> ou <code>templates/</code>) <b>nunca dispararia o workflow</b>. O GitHub ficaria indefinidamente aguardando o status check ser reportado, criando um <u>bloqueio perpétuo de merge</u>.<br/>"
        "• <i>Decisão:</i> O pipeline executa em todo PR. Dura ~1 min, elimina o risco de travar entregas e assegura auditoria contínua de IaC e containers.<br/><br/>"
        "<b>2. Política do OWASP ZAP (Flag -I e regras FAIL no .zap/rules.tsv):</b><br/>"
        "• <i>Contexto:</i> Em pipelines de CI, o ZAP roda localmente no runner em HTTP (127.0.0.1:5000), sem certificado TLS de produção.<br/>"
        "• <i>O Problema:</i> No modo padrão, o ZAP reprovaria o job por avisos informativos de ambiente (ex: cookie sem flag Secure em HTTP ou falta de HSTS), gerando falsos-positivos e fadiga de alertas. Desligar o scanner ou usar <code>continue-on-error</code>, porém, desarmaria a proteção.<br/>"
        "• <i>Decisão:</i> Execução com <code>-I</code> (ignorar warnings genéricos) somada ao arquivo <code>rules.tsv</code> versionado. Regras críticas de injeção (XSS 40012/40014, SQLi) e má configuração (CSP, anti-CSRF) são marcadas como <b>FAIL</b> (bloqueantes). Regras de infra/TLS no runner são documentadas como <b>WARN</b> com justificativa técnica formal.<br/>"
        "• Finalizar e abrir para perguntas.",
        "Para concluir, destacamos dois trade-offs cruciais de engenharia: primeiro, o iac-scan.yml não possui filtro 'paths:' porque, sendo Required Check, impediria o merge de qualquer PR que não mexesse em infraestrutura. Segundo, no DAST utilizamos a flag '-I' com a lista explícita de FAIL no rules.tsv para focar em vulnerabilidades reais sem ruídos informativos de ambiente local. Estamos à disposição para perguntas!"
    ))

    # Quebra de página para FAQ e Rubricas
    story.append(PageBreak())
    story.append(Paragraph("Perguntas Prováveis da Banca & Respostas Estratégicas", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    faq_data = [
        [Paragraph("<b>Pergunta da Banca</b>", bold_label), Paragraph("<b>Resposta Curta e Técnica</b>", bold_label)],
        [Paragraph("Por que o ZAP Baseline sozinho não pegava o XSS?", body_style),
         Paragraph("O Baseline é puramente passivo: só analisa respostas e headers. O XSS refletido só é comprovado quando injetamos payloads, por isso adicionamos o ZAP Full Scan ativo (10 min).", body_style)],
        [Paragraph("Por que não expuseram a porta do banco no host?", body_style),
         Paragraph("O SQLite opera em volume nomeado e roda exclusivamente na rede interna 'backend', sem mapeamento de porta para o host, eliminando qualquer superfície de ataque externa.", body_style)],
        [Paragraph("Por que desativaram a revisão de Code Owners no ruleset?", body_style),
         Paragraph("O repositório oficial é um fork (gustavolucen4) e o CODEOWNERS original apontava para @Shuralot. Manter a regra travaria o merge permanentemente por falta de permissão de um usuário externo.", body_style)],
        [Paragraph("Como garantem que senhas não chegam ao Loki?", body_style),
         Paragraph("Nosso logger JSON filtra ativamente e descarta chaves como password, token e csrf_token. Além disso, temos um teste automatizado (test_logs_are_json_without_secrets) que reprova o CI se senhas forem logadas.", body_style)]
    ]
    t_faq = Table(faq_data, colWidths=[180, 343])
    t_faq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_faq)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF gerado com sucesso em: {output_paths[0]}")

if __name__ == "__main__":
    out = "docs/Roteiro-Apresentacao-Atividade-2.pdf"
    if len(sys.argv) > 1:
        out = sys.argv[1]
    build_pdf([out])
