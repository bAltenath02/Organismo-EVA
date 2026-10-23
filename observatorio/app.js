let dados; let ativo = "exp001";
const mostrarBooleano = valor => `<span class="${valor ? "yes" : "no"}">${valor ? "moveu" : "não moveu"}</span>`;
function renderizar(){
  const exp = dados.experimentos[ativo];
  document.querySelector("#tabs").innerHTML = Object.entries(dados.experimentos).map(([chave,item]) => `<button class="tab ${chave===ativo?"active":""}" data-id="${chave}">${item.id}<small>${item.titulo}</small></button>`).join("");
  document.querySelectorAll(".tab").forEach(botao => botao.onclick = () => {ativo=botao.dataset.id;renderizar()});
  const metricas = exp.metricas.map(([nome,valor,estilo]) => `<div class="metric ${estilo}"><span>${nome}</span><strong>${valor}</strong></div>`).join("");
  const barras = exp.barras.map(([nome,valor]) => `<div class="barrow"><span>${nome}</span><div class="bar"><i style="width:${valor*100}%"></i></div><b>${Math.round(valor*100)}%</b></div>`).join("");
  const cabecalho = exp.colunas.map(nome => `<th>${nome}</th>`).join("");
  const linhas = exp.linhas.map(linha => `<tr><td>${linha[0]}</td><td>${linha[1]}</td>${linha.slice(2).map(valor => `<td>${mostrarBooleano(valor)}</td>`).join("")}</tr>`).join("");
  document.querySelector("#content").innerHTML = `<article class="card"><p class="kicker">${exp.id}</p><h2>${exp.titulo}</h2><p class="question">${exp.pergunta}</p><div class="metrics">${metricas}</div></article><div class="split"><article class="card"><p class="kicker">COMPARAÇÃO</p><h3>Desempenho observado</h3>${barras}</article><article class="card"><div class="head"><div><p class="kicker">EXECUÇÃO</p><h3>Resultados gerados agora</h3></div><button class="refresh" id="refresh">↻ Executar de novo</button></div><p class="question">O botão solicita novos dados ao servidor local, que executa os relatórios em Python antes de responder.</p></article></div><article class="card"><p class="kicker">RASTRO DE AVALIAÇÃO</p><h3>Casos não usados como experiências</h3><div class="tablewrap"><table><thead><tr>${cabecalho}</tr></thead><tbody>${linhas}</tbody></table></div></article><article class="card"><p class="kicker">LEITURA RESPONSÁVEL</p><h3>O que este resultado ainda não demonstra</h3><p class="limit">${exp.limitacao}</p><div class="next"><b>Próxima pergunta</b>${exp.proximo}</div></article>`;
  document.querySelector("#refresh").onclick = carregar;
}
async function carregar(){
  const resposta = await fetch(`dados_experimentos.json?agora=${Date.now()}`);
  dados = await resposta.json();
  document.querySelector("#timestamp").textContent = `Dados gerados em ${new Intl.DateTimeFormat("pt-BR",{dateStyle:"medium",timeStyle:"medium"}).format(new Date(dados.gerado_em))}`;
  renderizar();
}
carregar().catch(erro => {document.querySelector("#content").textContent=`Não foi possível carregar os resultados: ${erro.message}`});
