# Notas para entrevista — ab-testing-toolkit

Documento interno. Não faz parte da documentação pública do projeto.

---

## As 3 decisões técnicas mais importantes

### 1. `decide()` exige o lift mínimo que vale a pena, senão não responde

**O que fiz:** `minimum_worthwhile_lift` é parâmetro obrigatório. Não tem default.

**Por quê:** significância estatística não é critério de decisão. Com tráfego suficiente, qualquer
diferença vira significativa — inclusive uma de 0,3% que não paga o esforço de engenharia nem o risco
de regressão.

O veredito HOLD existe exatamente para isso: efeito real com 99,2% de probabilidade, lift de 3,0%,
barra de 5,0% → não envia. Esse é o caso que mais custa dinheiro na prática, porque o time lê
"significativo" e envia.

Se alguém não consegue nomear o menor efeito que mudaria a decisão, normalmente o teste não deveria
rodar.

### 2. Variância agrupada no teste, não agrupada no intervalo

**O que fiz:** o z-teste usa variância pooled; o intervalo de confiança usa unpooled.

**Por quê:** agrupar assume a hipótese nula verdadeira. Isso é correto quando você está **testando**
a nula, e errado quando está **estimando** o efeito — porque se o efeito existe, as duas proporções
não vêm da mesma distribuição.

É um detalhe que muita implementação erra usando pooled nos dois, e o intervalo sai levemente torto.

### 3. Validar o próprio teste por simulação

**O que fiz:** um teste que roda 2.000 experimentos A/A simulados e verifica se a taxa de falso
positivo cai perto de 5%.

**Por quê:** toda leitura de experimento construída em cima dessa função herda o erro dela. Se o teste
estiver mal calibrado, nenhum readout em cima é confiável, e isso não aparece em teste unitário comum.

Mesma lógica no CUPED: gerei dados com theta verdadeiro 0,7 e verifico se o estimador recupera.
Ferramenta que não consegue demonstrar a própria calibração não deveria decidir nada.

---

## 5 perguntas prováveis, com resposta

### 1. "Qual a diferença entre p-valor e P(B > A)?"

São probabilidades de coisas diferentes, e a troca é o erro mais comum em readout de experimento.

P-valor é `P(dado tão extremo quanto este | não existe efeito)`. É uma afirmação sobre os dados,
condicionada à nula ser verdadeira.

P(B > A) é `P(o tratamento é melhor | estes dados)`. É uma afirmação sobre o mundo, condicionada aos
dados.

"Estamos 95% confiantes de que a variante ganha" é a segunda frase colada no primeiro número. O
relatório imprime essa distinção no rodapé de todo readout, de propósito.

E o número que eu realmente levaria para a decisão é nenhum dos dois: é a **perda esperada**, que está
denominada em taxa de conversão. "Se eu enviar isso e estiver errado, perco em média 0,00008 de
conversão" é uma frase que um gestor consegue usar.

### 2. "Por que CUPED funciona? Não é trapaça reduzir variância?"

Não, porque não mexe no estimador do efeito — mexe no ruído em volta dele.

A ideia: o comportamento do usuário antes do experimento prevê parte do comportamento durante. Essa
parte previsível é ruído do ponto de vista do efeito do tratamento. Subtraindo ela, a variância cai e
a média fica intacta. Tem teste garantindo que a média não se move.

A condição que torna isso válido é uma só: a covariável tem que ser medida **antes da
randomização**. Aí ela não pode ter sido afetada pelo tratamento, e a estimativa continua não-viesada.

Usar covariável medida durante o experimento quebra exatamente isso — e é o único jeito de errar CUPED
feio. Está no docstring do módulo porque é o erro que eu veria alguém cometer.

No exemplo, correlação de 0,87 dá 75% de redução de variância, que equivale a 4x o tráfego. Um teste
de 12 dias vira 3.

### 3. "Um teste deu 10% de lift com p=0,26. O que você reporta?"

Reporto INCONCLUSIVO, não "sem diferença".

Com 5.000 usuários por variante e baseline de 5%, o menor efeito detectável é 25,9%. O teste nunca
teve poder para responder a pergunta. Dizer "não houve efeito" é afirmar algo que o experimento não
mediu.

Essa distinção importa porque as duas conclusões levam a ações opostas: "sem efeito" mata a
iniciativa; "inconclusivo" diz que a pergunta continua aberta e que, se ela importa, precisa de mais
tráfego ou de uma métrica mais sensível.

O `decide()` separa os dois casos explicitamente: STOP só sai quando o teste **tinha** poder e o
efeito não apareceu.

### 4. "O que falta aqui para uso em produção?"

Três coisas, e estão no README.

A mais séria é **teste sequencial**. Hoje o tamanho de amostra é fixo e a análise assume uma única
olhada nos dados. Na vida real todo mundo espia o dashboard todo dia, e espiar teste de horizonte fixo
infla muito o falso positivo. A correção honesta é alpha spending ou inferência sempre-válida, e não
está implementado.

Depois, correção para múltiplas comparações: quatro variantes contra um controle a 5% dá ~19% de
chance de pelo menos um falso positivo.

E independência: usuários da mesma casa, mesma sessão ou com efeito de rede não são independentes, e
aí o erro padrão sai pequeno demais.

### 5. "Só tem dado simulado. Isso não enfraquece o projeto?"

Aqui é o contrário, e eu defendo a escolha.

A pergunta deste projeto não é "o que aconteceu no experimento de alguma empresa". É "essa
implementação faz a conta certa". Isso só se verifica contra um processo cuja verdade você conhece.

Por isso a validação é por simulação: 2.000 testes A/A para conferir que a taxa de falso positivo bate
com o alpha, e dados gerados com theta conhecido para conferir que o CUPED recupera. Com dado real eu
não teria contra o que comparar.

É a mesma lógica do meu projeto de marketing mix modeling: quando a quantidade de interesse nunca é
observada, simular com parâmetros declarados é a única forma de **pontuar** o método em vez de só
olhar para o gráfico.

---

## Números para ter na ponta da língua

| | |
| --- | --- |
| Baseline 5%, MDE 5% relativo | 122.124 por variante |
| Mesmo plano, 20k/dia | 12,2 dias |
| MDE com 5.000 por variante | 25,9% relativo |
| MDE com 100.000 por variante | 5,5% relativo |
| Escala do tamanho de amostra | 1 / mde² (metade do efeito = 4x a amostra) |
| CUPED com correlação 0,87 | 75,3% menos variância = 4,05x tráfego |
| Validação de falso positivo | 2.000 testes A/A, alvo 5% |
| Testes | 15 |
