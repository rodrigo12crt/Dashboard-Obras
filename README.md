# 🏗️ Dashboard de Gestão: Venda e Reforma

Este é um dashboard interativo desenvolvido em **Python** utilizando **Streamlit**, focado na gestão financeira de um projeto imobiliário que envolve a venda de um imóvel e a gestão de custos de uma reforma detalhada.

O sistema permite o acompanhamento de pagamentos, previsão de término de parcelas e o cálculo do saldo final líquido após todas as saídas e investimentos em obras.

## 🚀 Funcionalidades

- **Gestão de Transação:** Entrada de valores fixos como valor de venda, comissões de corretagem, financiamento e partilha.
- **Controle de Obras:** Edição em tempo real de itens de reforma (Móveis, Piso, Pedreiro, etc.).
- **Cálculos Automáticos:**
    - Valor total pago vs. Valor a pagar por item.
    - Previsão automática do mês da última parcela.
    - Resumo financeiro dinâmico (Saldo Intermediário e Saldo Final).
- **Interface Inteligente:**
    - Linha de **TOTAL** automática no rodapé da tabela.
    - Coloração dinâmica: Itens quitados ficam destacados em verde.
    - Gráfico de pizza interativo para visualização da distribuição de gastos.
- **Persistência de Dados:** Integração com **SQLite3** para armazenamento local e seguro dos dados.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.12+
- **Framework Web:** [Streamlit](https://streamlit.io/)
- **Banco de Dados:** SQLite3
- **Análise de Dados:** Pandas
- **Gráficos:** Plotly Express
- **Infraestrutura:** AWS EC2 (Hospedagem gratuita na porta 80)

## 📂 Estrutura do Projeto

```text
├── dash.py              # Código principal da aplicação
├── reforma.db           # Banco de dados SQLite (gerado automaticamente)
├── requirements.txt     # Dependências do projeto
└── README.md            # Documentação
```
## 🔧 Como rodar localmente

# 1. Clone o repositório:

```
git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
cd seu-repositorio
```

# 2. Crie um ambiente virtual:

```
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

# 3. Instale as dependências:

```
pip install -r requirements.txt
```

# 4. Execute o App:

```
streamlit run dash.py
```

## 🌐 Hospedagem na AWS

A aplicação foi configurada para rodar em uma instância EC2 da AWS dentro do Free Tier.
 - Porta utilizada: 80 (HTTP) para facilitar o acesso em redes corporativas.
 - Processo: Gerenciado via nohup para execução 24/7.
