(() => {
  'use strict';

  const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)');
  const dado = document.getElementById('dadoGrande');
  const resultadoDado = document.getElementById('dadoResultado');
  const textoCena = document.getElementById('textoCena');
  const paragrafoCena = textoCena.closest('[aria-live]');
  const escolhas = document.getElementById('escolhas');
  let rolando = false;
  let indiceCena = 0;
  let digitando = false;
  let temporizadorTexto = 0;

  // Anima a rolagem e anuncia somente o resultado final.
  dado.addEventListener('click', () => {
    if (rolando) return;
    rolando = true;
    dado.disabled = true;
    resultadoDado.textContent = '';
    dado.classList.remove('rolando');
    void dado.offsetWidth;
    dado.classList.add('rolando');

    const duracao = movimentoReduzido.matches ? 0 : 1200;
    const intervalo = duracao ? window.setInterval(() => {
      dado.textContent = String(Math.floor(Math.random() * 20) + 1);
    }, 68) : null;

    window.setTimeout(() => {
      if (intervalo) window.clearInterval(intervalo);
      const valor = Math.floor(Math.random() * 20) + 1;
      dado.textContent = String(valor);
      if (valor === 20) resultadoDado.textContent = 'Acerto crítico! O destino sorri para você.';
      else if (valor === 1) resultadoDado.textContent = 'Falha crítica... o narrador está rindo.';
      else if (valor >= 11) resultadoDado.textContent = 'Boa rolagem! A aventura continua.';
      else resultadoDado.textContent = 'Hmm... o destino não está do seu lado.';
      dado.disabled = false;
      rolando = false;
    }, duracao);
  });

  // Cenas e escolhas da demonstração.
  const cenas = [
    {
      texto: 'A neblina cobre a estrada e, ao longe, uma luz trêmula na boca de uma caverna antiga. Você sente o peso da espada na cintura. Algo lá dentro respira. O que você faz?',
      escolhas: [
        { rotulo: 'Entrar na caverna', resultado: 'Você avança pela escuridão. O chão treme e dois olhos dourados se acendem diante de você. O narrador rola os dados... e a criatura recua, curiosa. Você ganhou alguns segundos.' },
        { rotulo: 'Apagar a tocha e escutar', resultado: 'No silêncio, você ouve passos pesados e uma voz rouca sussurrando seu nome. Os dados rolam: você não foi notado. Mas alguém sabe que você chegou.' },
        { rotulo: 'Voltar para a vila', resultado: 'Você dá as costas à caverna. A neblina se fecha atrás de você e, na vila, todas as portas estão trancadas. A história não ia deixar você fugir assim tão fácil.' }
      ]
    },
    {
      texto: 'O portão da cidade em ruínas range sozinho. Sobre o altar de pedra, um dado de ouro gira sem parar, sem que ninguém o toque. Cada volta faz as velas tremerem. O que você faz?',
      escolhas: [
        { rotulo: 'Pegar o dado de ouro', resultado: 'Seus dedos tocam o metal frio e as velas se apagam. Uma voz diz: "Agora você joga por mim". Os dados rolam, e o seu destino acaba de mudar de dono.' },
        { rotulo: 'Esperar o dado parar', resultado: 'O dado gira por uma eternidade e para no número 20. As paredes se abrem, revelando uma passagem secreta. A paciência foi recompensada.' },
        { rotulo: 'Quebrar o altar', resultado: 'A pedra racha e uma onda de luz roxa empurra você para trás. O dado desaparece, mas algo muito mais antigo acabou de acordar.' }
      ]
    },
    {
      texto: 'No porto, um barco sem tripulação balança nas ondas. Na proa há um mapa com o seu nome escrito, e a maré está subindo rápido. O que você faz?',
      escolhas: [
        { rotulo: 'Embarcar e seguir o mapa', resultado: 'As velas se enchem de vento sem que ninguém as toque. O narrador rola os dados e uma ilha surge no horizonte, exatamente onde o mapa apontava.' },
        { rotulo: 'Queimar o mapa', resultado: 'As chamas ficam azuis e o mapa se desfaz em cinzas que formam um novo desenho no ar. Você não escapa do destino, só o torna mais perigoso.' },
        { rotulo: 'Procurar quem deixou o barco', resultado: 'Na taverna, ninguém admite ter visto nada, mas um velho marinheiro desvia o olhar. Ele sabe de algo, e os dados dizem que ele está com medo.' }
      ]
    }
  ];

  function concluirTexto(depois) {
    digitando = false;
    paragrafoCena.setAttribute('aria-live', 'polite');
    if (depois) depois();
  }

  // Mostra a narração em etapas, ou inteira com movimento reduzido.
  function digitar(texto, depois) {
    window.clearTimeout(temporizadorTexto);
    digitando = true;
    paragrafoCena.setAttribute('aria-live', 'off');
    textoCena.textContent = '';

    if (movimentoReduzido.matches) {
      textoCena.textContent = texto;
      concluirTexto(depois);
      return;
    }

    let indice = 0;
    function proximaLetra() {
      indice += 1;
      textoCena.textContent = texto.slice(0, indice);
      if (indice < texto.length) temporizadorTexto = window.setTimeout(proximaLetra, 23);
      else concluirTexto(depois);
    }
    proximaLetra();
  }

  function mostrarCena() {
    const cena = cenas[indiceCena];
    escolhas.classList.remove('visivel');
    escolhas.replaceChildren();
    digitar(cena.texto, () => {
      cena.escolhas.forEach((escolha) => {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.textContent = escolha.rotulo;
        botao.addEventListener('click', () => escolher(escolha));
        escolhas.appendChild(botao);
      });
      escolhas.classList.add('visivel');
    });
  }

  function escolher(escolha) {
    if (digitando) return;
    escolhas.classList.remove('visivel');
    escolhas.replaceChildren();
    digitar(escolha.resultado, () => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.textContent = 'Continuar a história';
      botao.addEventListener('click', () => {
        indiceCena = (indiceCena + 1) % cenas.length;
        mostrarCena();
      });
      escolhas.appendChild(botao);
      escolhas.classList.add('visivel');
    });
  }

  mostrarCena();

  // Revela seções ao rolar sem ocultar conteúdo quando o script falha.
  const secoes = document.querySelectorAll('.secao-revelar');
  if ('IntersectionObserver' in window && !movimentoReduzido.matches) {
    document.body.classList.add('js');
    const observador = new IntersectionObserver((entradas, atual) => {
      entradas.forEach((entrada) => {
        if (entrada.isIntersecting) {
          entrada.target.classList.add('visivel');
          atual.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -30px 0px' });
    secoes.forEach((secao) => observador.observe(secao));
  }

  // Desenha poucas partículas e pausa fora da aba visível.
  const canvas = document.getElementById('particulas');
  const contexto = canvas.getContext('2d');
  const telaPequena = window.matchMedia('(max-width: 600px)');
  let largura = 0;
  let altura = 0;
  let escala = 1;
  let particulas = [];
  let quadro = 0;

  function semearParticulas() {
    const total = telaPequena.matches ? 16 : 38;
    particulas = Array.from({ length: total }, () => ({
      x: Math.random() * largura,
      y: Math.random() * altura,
      raio: Math.random() * 1.3 + .35,
      fase: Math.random() * Math.PI * 2,
      velocidade: Math.random() * .16 + .045,
      cor: Math.random() > .65 ? '232,160,176' : '212,175,55'
    }));
  }

  function pintar(animar = true) {
    contexto.clearRect(0, 0, largura, altura);
    particulas.forEach((ponto) => {
      if (animar) {
        ponto.y -= ponto.velocidade;
        ponto.fase += .014;
        if (ponto.y < -4) {
          ponto.y = altura + 4;
          ponto.x = Math.random() * largura;
        }
      }
      const alfa = .12 + (Math.sin(ponto.fase) + 1) * .1;
      contexto.beginPath();
      contexto.arc(ponto.x, ponto.y, ponto.raio, 0, Math.PI * 2);
      contexto.fillStyle = `rgba(${ponto.cor}, ${alfa})`;
      contexto.fill();
    });
    if (animar) quadro = window.requestAnimationFrame(() => pintar(true));
  }

  function ajustarCanvas() {
    escala = Math.min(window.devicePixelRatio || 1, 1.35);
    largura = window.innerWidth;
    altura = window.innerHeight;
    canvas.width = Math.round(largura * escala);
    canvas.height = Math.round(altura * escala);
    contexto.setTransform(escala, 0, 0, escala, 0, 0);
    semearParticulas();
    pintar(false);
  }

  function atualizarParticulas() {
    window.cancelAnimationFrame(quadro);
    if (!document.hidden && !movimentoReduzido.matches) pintar(true);
  }

  window.addEventListener('resize', ajustarCanvas, { passive: true });
  document.addEventListener('visibilitychange', atualizarParticulas);
  telaPequena.addEventListener('change', ajustarCanvas);
  movimentoReduzido.addEventListener('change', atualizarParticulas);
  ajustarCanvas();
  atualizarParticulas();
})();
