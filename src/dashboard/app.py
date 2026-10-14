"""Dashboard interativo de monitoramento de custos AWS e FinOps com Streamlit.

Executa visualizações em tempo real a partir do AWS Cost Explorer ou a partir
do histórico de execuções persistido localmente em SQLite.
"""

import pandas as pd
import streamlit as st

from src import config
from src.ai.llama_client import LlamaUnavailableError, interpret
from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import CostExplorerError, get_costs
from src.database.repository import get_history, get_latest_run, get_run_services, save_run


def format_money(val):
    return f"${val:,.2f}"


def run_dashboard():
    st.set_page_config(
        page_title="AWS Cost Monitor — FinOps",
        page_icon="💸",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Cabeçalho da aplicação
    st.title("💸 AWS Cost Monitor — FinOps Dashboard")
    st.caption("Visibilidade de gastos, regras determinísticas de FinOps e interpretação por IA.")

    # Sidebar: Filtros e Configurações
    st.sidebar.header("⚙️ Configurações & Filtros")

    mode = st.sidebar.radio(
        "Fonte de Dados",
        ["Consulta AWS em Tempo Real", "Histórico Local (SQLite)"],
        index=0,
    )

    costs = None
    analysis = None
    comparison = None
    alerts = []
    ai_interpretation = None
    ai_error = None
    period_label = ""

    if mode == "Consulta AWS em Tempo Real":
        days = st.sidebar.slider("Janela de Análise (Dias)", min_value=7, max_value=90, value=30, step=1)
        granularity = st.sidebar.selectbox("Granularidade", ["DAILY", "MONTHLY"], index=0)
        tag_input = st.sidebar.text_input("Agrupar por Tag (Opcional, ex: Environment)", value="")
        enable_ai = st.sidebar.checkbox("Habilitar Análise de IA", value=config.AI_ENABLED)

        tag_key = tag_input.strip() if tag_input.strip() else None

        if st.sidebar.button("🔄 Atualizar Consulta AWS", use_container_width=True):
            st.cache_data.clear()

        with st.spinner("Consultando AWS Cost Explorer..."):
            try:
                costs = get_costs(
                    period_days=days,
                    granularity=granularity,
                    tag_key=tag_key,
                )
            except CostExplorerError as err:
                st.error(f"⚠️ Erro ao consultar a AWS: {err}")
                st.info("Dica: Você pode visualizar os dados pelo modo 'Histórico Local (SQLite)' ou configurar suas credenciais com 'aws configure'.")
                return

        if not costs:
            st.warning("O Cost Explorer não retornou custos para o período selecionado.")
            return

        analysis = analyze_costs(costs)
        comparison = compare_periods(costs)
        alerts = generate_alerts(analysis, comparison)
        period_label = f"{costs[0]['start']} até {costs[-1]['end']}"

        # IA opcional
        if enable_ai:
            try:
                ai_interpretation = interpret(analysis, comparison, alerts)
            except LlamaUnavailableError as lerr:
                ai_error = str(lerr)

        # Salva snapshot automaticamente no SQLite
        try:
            save_run(
                costs=costs,
                analysis=analysis,
                comparison=comparison,
                ai_interpretation=ai_interpretation,
                alerts=alerts,
            )
        except Exception:
            pass

    else:
        # Modo Histórico Local
        history = get_history(limit=50)
        if not history:
            st.info("Nenhuma execução gravada no banco local ainda. Execute uma consulta na AWS primeiro.")
            return

        run_options = {
            f"ID #{r['id']} — {r['created_at'][:19]} (${r['total_cost']:.2f})": r["id"]
            for r in reversed(history)
        }
        selected_run_label = st.sidebar.selectbox("Selecione a Execução", list(run_options.keys()))
        selected_run_id = run_options[selected_run_label]

        # Carrega dados do run selecionado
        selected_run = next(r for r in history if r["id"] == selected_run_id)
        services_db = get_run_services(selected_run_id)

        period_label = f"{selected_run['period_start']} até {selected_run['period_end']}"
        alerts = selected_run["alerts"]
        ai_interpretation = selected_run["ai_interpretation"]

        # Reconstrói estruturas para o dashboard
        analysis = {
            "total_cost": selected_run["total_cost"],
            "has_positive_cost": bool(selected_run["has_positive_cost"]),
            "largest_service": selected_run["largest_service"],
            "positive_services": {s["service_name"]: s["amount"] for s in services_db},
            "percentages": {s["service_name"]: s["percentage"] for s in services_db},
        }
        comparison = None
        if selected_run["previous_total"] is not None:
            comparison = {
                "previous_total": selected_run["previous_total"],
                "current_total": selected_run["total_cost"],
                "variation": selected_run["variation"],
            }

    # ==========================
    # 1. KPIs no Topo
    # ==========================
    st.markdown(f"**Período Analisado:** `{period_label}`")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💵 Custo Total",
            value=format_money(analysis["total_cost"]),
            help="Soma de todos os custos no período analisado.",
        )

    with col2:
        if comparison and comparison["variation"] is not None:
            var_val = comparison["variation"]
            delta_str = f"{var_val:+.1f}%"
            # Delta invertido para custos: aumento é vermelho (inverse), redução é verde
            st.metric(
                label="📈 Variação vs. Anterior",
                value=delta_str,
                delta=f"{var_val:+.1f}% vs anterior",
                delta_color="inverse",
            )
        else:
            st.metric(label="📈 Variação vs. Anterior", value="N/A", help="Sem período anterior para base.")

    with col3:
        largest = analysis["largest_service"] or "Nenhum"
        largest_pct = analysis["percentages"].get(largest, 0.0)
        st.metric(
            label="🏆 Maior Serviço",
            value=largest,
            delta=f"{largest_pct:.1f}% do total" if largest != "Nenhum" else None,
            delta_color="off",
        )

    with col4:
        st.metric(
            label="🚨 Alertas de FinOps",
            value=len(alerts),
            help="Alertas de concentração, variação e ranking disparados.",
        )

    st.divider()

    # ==========================
    # 2. Parecer de IA (se houver)
    # ==========================
    if ai_interpretation:
        with st.expander("🤖 Parecer do Analista FinOps (IA Local / Llama)", expanded=True):
            st.markdown(ai_interpretation)
    elif ai_error:
        with st.expander("⚠️ Status da IA"):
            st.warning(f"Camada de IA indisponível: {ai_error}")

    # ==========================
    # 3. Gráficos e Distribuição
    # ==========================
    st.subheader("📊 Análise Visual de Gastos")
    col_chart_left, col_chart_right = st.columns([3, 2])

    with col_chart_left:
        # Gráfico temporal se houver múltiplos períodos (ex: DAILY)
        if costs and len(costs) > 1:
            st.markdown("##### 📅 Evolução Temporal dos Custos")
            timeline_data = []
            for p in costs:
                p_date = p["start"]
                for g in p.get("groups", []):
                    srv_name = g["Keys"][0]
                    srv_amt = float(g["Metrics"]["UnblendedCost"]["Amount"])
                    if srv_amt > 0:
                        timeline_data.append({"Data": p_date, "Serviço": srv_name, "Custo (USD)": srv_amt})

            if timeline_data:
                df_time = pd.DataFrame(timeline_data)
                pivot_df = df_time.pivot_table(index="Data", columns="Serviço", values="Custo (USD)", fill_value=0)
                st.bar_chart(pivot_df)
            else:
                st.info("Nenhum custo detalhado por dia encontrado.")
        else:
            # Alternativa: Gráfico de barras horizontal dos maiores serviços
            st.markdown("##### 🏢 Ranking de Custos por Serviço")
            if analysis["positive_services"]:
                df_services = pd.DataFrame(
                    [
                        {"Serviço": k, "Custo (USD)": v}
                        for k, v in sorted(analysis["positive_services"].items(), key=lambda x: x[1], reverse=True)
                    ]
                )
                st.bar_chart(df_services.set_index("Serviço"))

    with col_chart_right:
        st.markdown("##### 🍰 Participação no Custo Total (%)")
        if analysis["positive_services"]:
            df_pie = pd.DataFrame(
                [
                    {"Serviço": k, "Participação (%)": v}
                    for k, v in sorted(analysis["percentages"].items(), key=lambda x: x[1], reverse=True)
                ]
            )
            st.dataframe(
                df_pie.style.format({"Participação (%)": "{:.1f}%"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhum serviço com custo positivo.")

    st.divider()

    # ==========================
    # 4. Detalhamento e Exportação
    # ==========================
    st.subheader("📋 Tabela Detalhada de Serviços")
    if analysis["positive_services"]:
        full_table = [
            {
                "Serviço": srv,
                "Custo (USD)": amt,
                "Participação (%)": analysis["percentages"].get(srv, 0.0),
            }
            for srv, amt in sorted(analysis["positive_services"].items(), key=lambda x: x[1], reverse=True)
        ]
        df_full = pd.DataFrame(full_table)
        st.dataframe(
            df_full.style.format({
                "Custo (USD)": "${:,.2f}",
                "Participação (%)": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df_full.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar Dados para CSV",
            data=csv_data,
            file_name="aws_cost_report.csv",
            mime="text/csv",
        )

    # ==========================
    # 5. Central de Alertas FinOps
    # ==========================
    st.subheader("🚨 Central de Alertas e Recomendações FinOps")
    if alerts:
        for al in alerts:
            sev = al["severity"].lower()
            msg = al["message"]
            if sev == "warning":
                st.warning(f"**[ALERTA - {sev.upper()}]** {msg}")
            elif sev == "info":
                st.info(f"**[INFO - {sev.upper()}]** {msg}")
            else:
                st.error(f"**[CRÍTICO - {sev.upper()}]** {msg}")
    else:
        st.success("✅ Nenhum alerta de desperdício ou anomalia detectado para o período.")


if __name__ == "__main__":
    run_dashboard()
