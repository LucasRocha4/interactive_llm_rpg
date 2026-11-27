(() => {
  'use strict';

  const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)');
  const dado = document.getElementById('dadoGrande');
  const resultadoDado = document.getElementById('dadoResultado');
  const textoCena = document.getElementById('textoCena');
  const paragrafoCena = textoCena.closest('[aria-live]');
  const escolhas = document.getElementById('escolhas');
  const confirmacaoEscolha = document.getElementById('confirmacaoEscolha');
  const cenaElemento = document.getElementById('cena');
  const seloNarrador = document.querySelector('.cena-selo');
  const reliquia = document.querySelector('.reliquia');
  const efeitosDestino = document.getElementById('efeitosDestino');
  const estrelaCadente = document.getElementById('estrelaCadente');
  let rolando = false;
  let indiceCena = 0;
  let digitando = false;
  let escolhaPendente = false;
  let temporizadorTexto = 0;
  let temporizadorEfeito = 0;
  let temporizadorEstrela = 0;
  let quadroParallax = 0;

  const espera = (milissegundos) => new Promise((resolver) => window.setTimeout(resolver, milissegundos));

  function centroDoDado() {
    const caixa = dado.getBoundingClientRect();
    return { x: caixa.left + caixa.width / 2, y: caixa.top + caixa.height / 2 };
  }

  // Emite anéis e faíscas a partir do dado nos resultados críticos.
  function manifestarDestino(valor) {
    if ((valor !== 20 && valor !== 1) || movimentoReduzido.matches) return;
    const critico = valor === 20 ? 'critico-20' : 'critico-1';
    const centro = centroDoDado();
    document.body.classList.remove('resultado-critico-20', 'resultado-critico-1');
    document.body.classList.add(`resultado-${critico}`);
    efeitosDestino.className = `efeitos-destino efeitos-destino--${critico}`;
    efeitosDestino.style.setProperty('--origem-x', `${centro.x}px`);
    efeitosDestino.style.setProperty('--origem-y', `${centro.y}px`);
    efeitosDestino.style.setProperty('--escala-anel', String(Math.ceil(Math.hypot(window.innerWidth, window.innerHeight) / 18)));
    efeitosDestino.replaceChildren();

    for (let indice = 0; indice < 3; indice += 1) {
      const anel = document.createElement('span');
      anel.className = 'anel-destino';
      anel.style.setProperty('--atraso', `${indice * 170}ms`);
      efeitosDestino.appendChild(anel);
    }
    for (let indice = 0; indice < 30; indice += 1) {
      const particula = document.createElement('span');
      const angulo = Math.random() * Math.PI * 2;
      const distancia = 70 + Math.random() * Math.min(window.innerWidth, window.innerHeight) * .48;
      particula.className = 'particula-destino';
      particula.style.setProperty('--dx', `${Math.cos(angulo) * distancia}px`);
      particula.style.setProperty('--dy', `${Math.sin(angulo) * distancia}px`);
      particula.style.setProperty('--atraso', `${Math.random() * 170}ms`);
      efeitosDestino.appendChild(particula);
    }

    seloNarrador.classList.add('pulso-destino');
    window.clearTimeout(temporizadorEfeito);
    temporizadorEfeito = window.setTimeout(() => {
      document.body.classList.remove('resultado-critico-20', 'resultado-critico-1');
      efeitosDestino.replaceChildren();
      seloNarrador.classList.remove('pulso-destino');
    }, 1900);
  }

  function atualizarInclinacaoDado(evento) {
    if (evento.pointerType === 'touch') return;
    const caixa = reliquia.getBoundingClientRect();
    const x = (evento.clientX - caixa.left) / caixa.width;
    const y = (evento.clientY - caixa.top) / caixa.height;
    dado.style.setProperty('--inclinacao-x', `${(0.5 - y) * 11}deg`);
    dado.style.setProperty('--inclinacao-y', `${(x - 0.5) * 11}deg`);
    dado.style.setProperty('--reflexo-x', `${Math.round(x * 100)}%`);
    dado.style.setProperty('--reflexo-y', `${Math.round(y * 100)}%`);
  }

  reliquia.addEventListener('pointermove', atualizarInclinacaoDado);
  reliquia.addEventListener('pointerleave', () => {
    dado.style.setProperty('--inclinacao-x', '0deg');
    dado.style.setProperty('--inclinacao-y', '0deg');
    dado.style.setProperty('--reflexo-x', '50%');
    dado.style.setProperty('--reflexo-y', '20%');
  });

  // Anima a rolagem e anuncia somente o resultado final.
  dado.addEventListener('click', async () => {
    if (rolando) return;
    rolando = true;
    dado.disabled = true;
    document.body.classList.remove('resultado-critico-20', 'resultado-critico-1');
    efeitosDestino.replaceChildren();
    window.clearTimeout(temporizadorEfeito);
    seloNarrador.classList.remove('pulso-destino');
    resultadoDado.textContent = '';
    dado.classList.remove('rolando');
    dado.classList.add('preparando');
    await espera(movimentoReduzido.matches ? 0 : 360);
    dado.classList.remove('preparando');
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
      manifestarDestino(valor);
      dado.disabled = false;
      rolando = false;
    }, duracao);
  });

  // Cenas e escolhas da demonstração.
  const cenas = [
    {
      tom: 'sombria',
      texto: 'A neblina cobre a estrada e, ao longe, uma luz trêmula na boca de uma caverna antiga. Você sente o peso da espada na cintura. Algo lá dentro respira. O que você faz?',
      escolhas: [
        { rotulo: 'Entrar na caverna', tom: 'combate', resultado: 'Você avança pela escuridão. O chão treme e dois olhos dourados se acendem diante de você. O narrador rola os dados... e a criatura recua, curiosa. Você ganhou alguns segundos.' },
        { rotulo: 'Apagar a tocha e escutar', tom: 'magica', resultado: 'No silêncio, você ouve passos pesados e uma voz rouca sussurrando seu nome. Os dados rolam: você não foi notado. Mas alguém sabe que você chegou.' },
        { rotulo: 'Voltar para a vila', tom: 'sombria', resultado: 'Você dá as costas à caverna. A neblina se fecha atrás de você e, na vila, todas as portas estão trancadas. A história não ia deixar você fugir assim tão fácil.' }
      ]
    },
    {
      tom: 'magica',
      texto: 'O portão da cidade em ruínas range sozinho. Sobre o altar de pedra, um dado de ouro gira sem parar, sem que ninguém o toque. Cada volta faz as velas tremerem. O que você faz?',
      escolhas: [
        { rotulo: 'Pegar o dado de ouro', tom: 'sombria', resultado: 'Seus dedos tocam o metal frio e as velas se apagam. Uma voz diz: "Agora você joga por mim". Os dados rolam, e o seu destino acaba de mudar de dono.' },
        { rotulo: 'Esperar o dado parar', tom: 'magica', resultado: 'O dado gira por uma eternidade e para no número 20. As paredes se abrem, revelando uma passagem secreta. A paciência foi recompensada.' },
        { rotulo: 'Quebrar o altar', tom: 'combate', resultado: 'A pedra racha e uma onda de luz roxa empurra você para trás. O dado desaparece, mas algo muito mais antigo acabou de acordar.' }
      ]
    },
    {
      tom: 'neutra',
      texto: 'No porto, um barco sem tripulação balança nas ondas. Na proa há um mapa com o seu nome escrito, e a maré está subindo rápido. O que você faz?',
      escolhas: [
        { rotulo: 'Embarcar e seguir o mapa', tom: 'magica', resultado: 'As velas se enchem de vento sem que ninguém as toque. O narrador rola os dados e uma ilha surge no horizonte, exatamente onde o mapa apontava.' },
        { rotulo: 'Queimar o mapa', tom: 'sombria', resultado: 'As chamas ficam azuis e o mapa se desfaz em cinzas que formam um novo desenho no ar. Você não escapa do destino, só o torna mais perigoso.' },
        { rotulo: 'Procurar quem deixou o barco', tom: 'neutra', resultado: 'Na taverna, ninguém admite ter visto nada, mas um velho marinheiro desvia o olhar. Ele sabe de algo, e os dados dizem que ele está com medo.' }
      ]
    }
  ];

  function definirTom(tom) {
    document.body.dataset.tom = tom;
    cenaElemento.dataset.tom = tom;
    cenaElemento.classList.remove('mudando-tom');
    void cenaElemento.offsetWidth;
    cenaElemento.classList.add('mudando-tom');
    window.setTimeout(() => cenaElemento.classList.remove('mudando-tom'), 650);
  }

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
    textoCena.replaceChildren();

    const partes = texto.split(/(magia|dragão|espada|tesouro|caverna)/giu).map((parte) => {
      const destaque = /^(magia|dragão|espada|tesouro|caverna)$/iu.test(parte);
      const elemento = destaque ? document.createElement('span') : document.createTextNode('');
      if (destaque) {
        elemento.className = 'palavra-chave aguardando-foco';
        textoCena.appendChild(elemento);
      } else {
        textoCena.appendChild(elemento);
      }
      const nodoTexto = destaque ? document.createTextNode('') : elemento;
      if (destaque) elemento.appendChild(nodoTexto);
      return { texto: Array.from(parte), destaque, elemento: nodoTexto };
    });

    if (movimentoReduzido.matches) {
      partes.forEach((parte) => {
        parte.elemento.textContent = parte.texto.join('');
        if (parte.destaque) parte.elemento.parentElement.classList.remove('aguardando-foco');
      });
      concluirTexto(depois);
      return;
    }

    let parteAtual = 0;
    let caractereAtual = 0;
    function proximaLetra() {
      while (parteAtual < partes.length && caractereAtual >= partes[parteAtual].texto.length) {
        const parte = partes[parteAtual];
        if (parte.destaque) {
          const destaque = parte.elemento.parentElement;
          destaque.classList.remove('aguardando-foco');
          destaque.classList.add('palavra-em-foco');
          window.setTimeout(() => destaque.classList.remove('palavra-em-foco'), 1100);
        }
        parteAtual += 1;
        caractereAtual = 0;
      }
      if (parteAtual >= partes.length) {
        concluirTexto(depois);
        return;
      }
      const parte = partes[parteAtual];
      const caractere = parte.texto[caractereAtual];
      parte.elemento.textContent += caractere;
      caractereAtual += 1;
      temporizadorTexto = window.setTimeout(proximaLetra, /[,.;:!?…]/u.test(caractere) ? 105 : 19);
    }
    proximaLetra();
  }

  function mostrarCena() {
    const cena = cenas[indiceCena];
    escolhaPendente = false;
    confirmacaoEscolha.textContent = '';
    definirTom(cena.tom);
    cenaElemento.classList.add('transicao-cena');
    window.setTimeout(() => cenaElemento.classList.remove('transicao-cena'), 420);
    escolhas.classList.remove('visivel');
    escolhas.replaceChildren();
    digitar(cena.texto, () => {
      cena.escolhas.forEach((escolha) => {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.textContent = escolha.rotulo;
        botao.addEventListener('click', () => escolher(escolha, botao));
        escolhas.appendChild(botao);
      });
      escolhas.classList.add('visivel');
    });
  }

  async function escolher(escolha, selecionada) {
    if (digitando || escolhaPendente) return;
    escolhaPendente = true;
    definirTom(escolha.tom);
    confirmacaoEscolha.textContent = `Você escolheu: ${escolha.rotulo}`;
    escolhas.querySelectorAll('button').forEach((botao) => {
      botao.disabled = true;
      botao.classList.toggle('selecionada', botao === selecionada);
      botao.classList.toggle('descartada', botao !== selecionada);
      if (botao === selecionada) botao.setAttribute('aria-pressed', 'true');
    });
    await espera(movimentoReduzido.matches ? 0 : 720);
    escolhas.classList.remove('visivel');
    await espera(movimentoReduzido.matches ? 0 : 280);
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

  // Repete o brilho dourado do hub e pausa fora da aba visível.
  const canvas = document.getElementById('particulas');
  const contexto = canvas.getContext('2d');
  const telaPequena = window.matchMedia('(max-width: 600px)');
  let largura = 0;
  let altura = 0;
  let escala = 1;
  let particulas = [];
  let quadro = 0;

  function novaParticula(aleatoriaNaTela) {
    return {
      x: Math.random() * largura,
      y: aleatoriaNaTela ? Math.random() * altura : altura + 10,
      raio: Math.random() * 2 + .5,
      velocidade: Math.random() * .6 + .2,
      balanco: Math.random() * Math.PI * 2,
      brilho: Math.random() * .6 + .3
    };
  }

  function semearParticulas() {
    const total = telaPequena.matches ? 24 : 60;
    particulas = Array.from({ length: total }, () => novaParticula(true));
  }

  function corDoTom() {
    const cores = {
      neutra: '230, 199, 90',
      combate: '228, 91, 86',
      magica: '155, 190, 255',
      sombria: '157, 105, 126'
    };
    return cores[document.body.dataset.tom] || cores.neutra;
  }

  function pintar(animar = true) {
    contexto.clearRect(0, 0, largura, altura);
    const cor = corDoTom();
    const tom = document.body.dataset.tom;
    const ritmo = tom === 'sombria' ? .36 : tom === 'magica' ? .62 : tom === 'combate' ? 1.4 : 1;
    particulas.forEach((ponto, indice) => {
      if (animar) {
        ponto.y -= ponto.velocidade * ritmo;
        ponto.balanco += .02 * ritmo;
        ponto.x += Math.sin(ponto.balanco) * .4 * ritmo;
        if (ponto.y < -10) particulas[indice] = novaParticula(false);
      }
      contexto.beginPath();
      contexto.arc(ponto.x, ponto.y, ponto.raio, 0, Math.PI * 2);
      contexto.fillStyle = `rgba(${cor}, ${ponto.brilho})`;
      contexto.shadowBlur = 8;
      contexto.shadowColor = `rgba(${cor}, .9)`;
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
    programarEstrela();
  }

  function programarEstrela() {
    window.clearTimeout(temporizadorEstrela);
    if (document.hidden || movimentoReduzido.matches) return;
    temporizadorEstrela = window.setTimeout(() => {
      estrelaCadente.style.setProperty('--estrela-x', `${55 + Math.random() * 40}%`);
      estrelaCadente.style.setProperty('--estrela-y', `${Math.random() * 40}%`);
      estrelaCadente.classList.remove('ativa');
      void estrelaCadente.offsetWidth;
      estrelaCadente.classList.add('ativa');
      programarEstrela();
    }, 5000 + Math.random() * 8000);
  }

  const elementosParallax = document.querySelectorAll('.luz, .sigilo');
  function atualizarParallax() {
    if (quadroParallax) return;
    quadroParallax = window.requestAnimationFrame(() => {
      const rolagem = movimentoReduzido.matches ? 0 : window.scrollY;
      elementosParallax.forEach((elemento, indice) => {
        elemento.style.setProperty('--parallax-y', `${-Math.round(rolagem * (.025 + indice * .009))}px`);
      });
      quadroParallax = 0;
    });
  }

  window.addEventListener('resize', ajustarCanvas, { passive: true });
  document.addEventListener('visibilitychange', atualizarParticulas);
  window.addEventListener('scroll', atualizarParallax, { passive: true });
  telaPequena.addEventListener('change', ajustarCanvas);
  movimentoReduzido.addEventListener('change', atualizarParticulas);
  movimentoReduzido.addEventListener('change', atualizarParallax);
  ajustarCanvas();
  atualizarParallax();
  atualizarParticulas();
})();
