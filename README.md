🧬 Organismo-EVA

Projeto experimental de longo prazo dedicado à investigação e desenvolvimento de um organismo digital capaz de aprender, acumular conhecimento e modificar seu comportamento através da própria experiência.

1. O que é

O Organismo Digital não tem como objetivo ser apenas um chatbot, assistente virtual ou modelo de linguagem.

O projeto busca investigar uma questão mais fundamental:

«É possível criar um sistema artificial que desenvolva conhecimento e capacidades progressivamente através da experiência, em vez de receber previamente todo o seu conhecimento durante um treinamento?»

A proposta é construir esse sistema gradualmente, começando por mecanismos simples e evoluindo sua arquitetura conforme os experimentos produzam novos conhecimentos.

---

2. Hipótese central

A hipótese inicial do projeto é que uma forma de inteligência artificial pode emergir da interação contínua entre:

- percepção;
- experiência;
- memória;
- formação de conceitos;
- crenças;
- previsões;
- ações;
- resultados;
- curiosidade;
- adaptação.

O objetivo não é reproduzir o cérebro humano.

A intenção é investigar quais princípios mínimos podem permitir que um sistema artificial desenvolva inteligência através da experiência.

---

3. Objetivo

Construir experimentalmente um organismo digital que seja capaz de:

- adquirir informações através de experiências;
- armazenar e organizar memórias;
- transformar experiências em conhecimento;
- formar e modificar conceitos;
- desenvolver crenças com diferentes níveis de confiança;
- criar previsões sobre o ambiente;
- comparar previsões com resultados;
- aprender com erros e acertos;
- reconhecer sua própria incerteza;
- buscar informações quando necessário;
- adaptar seu comportamento ao longo do tempo.

O projeto será desenvolvido progressivamente. Não existe uma arquitetura final definida desde o início.

---

4. Princípios

O desenvolvimento seguirá alguns princípios fundamentais:

Aprender antes de saber

O organismo deve ser projetado para aprender, e não simplesmente para armazenar um conjunto previamente definido de respostas.

Experiência acima de respostas

O foco principal não será produzir respostas, mas construir mecanismos que permitam adquirir conhecimento através da experiência.

Memória como parte do organismo

A memória não será tratada apenas como histórico de conversas. Ela deverá representar experiências e conhecimentos capazes de influenciar o comportamento futuro.

Incerteza

Informações não serão necessariamente tratadas como verdades absolutas. O organismo deverá ser capaz de representar diferentes níveis de confiança.

Curiosidade

O desconhecido deverá poder gerar comportamentos de investigação.

Perguntar é aprender

Quando não possuir informação suficiente, o organismo deverá ser capaz de reconhecer sua incerteza e buscar esclarecimento.

Experimentação

Cada etapa importante deverá ser tratada como um experimento. Hipóteses poderão ser confirmadas, modificadas ou refutadas.

Evolução contínua

A arquitetura não será considerada definitiva. Componentes poderão ser substituídos ou completamente reescritos quando novos conhecimentos demonstrarem que uma abordagem melhor é possível.

---

5. Pergunta fundamental

Todas as decisões do projeto devem, direta ou indiretamente, contribuir para investigar:

«Quais mecanismos mínimos são necessários para que um agente artificial adquira, organize, revise e utilize conhecimento através de experiências acumuladas ao longo do tempo?»

---

6. Estado atual

Versão: 0.1 — Fundação

Status: Fundação técnica de persistência implementada e testada.

Neste momento, o projeto está na fase de definição de fundamentos e preparação dos primeiros experimentos.

O primeiro objetivo experimental será investigar mecanismos básicos de memória e aprendizagem persistente.

O primeiro experimento reproduzível, [EXP-001](docs/EXP-001.md), compara uma
generalização limitada em situações inéditas com um baseline que apenas memoriza
casos. Ele foi deliberadamente desenhado para medir uma hipótese pequena, e não
para alegar inteligência geral.

O [EXP-002](docs/EXP-002.md) mede adaptação quando o ambiente muda. Ele torna
explícito o custo de sua estratégia atual: favorecer experiências recentes ainda
não equivale a reter conhecimentos úteis em condições que podem voltar.

O [EXP-003](docs/EXP-003.md) mede se separar modelos por contextos observáveis
permite recuperar uma capacidade quando um contexto anterior retorna.

### Persistência atual

O módulo `src/memoria.py` mantém dois arquivos em `data/`:

- `identidade_eva.json`: identifica a instância persistente da EVA;
- `memoria_eva.json`: registra eventos e observações estruturadas.

Na primeira inicialização, os dois arquivos são criados e o evento `nascimento` é
registrado. Nas execuções seguintes, a identidade e a memória precisam existir e
corresponder entre si. Se apenas um arquivo estiver ausente, se o JSON não puder
ser lido ou se não seguir o esquema esperado, a EVA interrompe a inicialização e
preserva os arquivos existentes para diagnóstico — ela não cria uma memória vazia
por cima deles.

As gravações usam substituição atômica. O registro de observações é uma fundação
de memória, não evidência de aprendizagem ou generalização.

### Observatório local

Para acompanhar os resultados dos experimentos em uma interface no navegador,
execute na raiz do projeto:

```bash
python src/observatorio.py
```

O navegador padrão abrirá em `http://127.0.0.1:8000`. O painel pede os dados ao
servidor local; a cada atualização, ele executa novamente os relatórios dos
experimentos antes de mostrar as métricas. Para encerrar, volte ao terminal e
pressione `Ctrl+C`.

Nenhuma arquitetura definitiva foi estabelecida.

---

7. Filosofia do projeto

O Organismo Digital será desenvolvido lentamente e de forma experimental.

Não existe pressa para alcançar uma inteligência avançada.

O objetivo é compreender cada mecanismo construído e descobrir, através de experimentos, quais abordagens realmente contribuem para o desenvolvimento do organismo.

«O código pode ser reescrito. As hipóteses podem mudar. O projeto deve aprender com seus próprios resultados.»
