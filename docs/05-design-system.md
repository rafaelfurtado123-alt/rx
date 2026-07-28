# Néfron — Design System `néfron·`

Design System de referência (Etapa 2). Padrão visual 2026: **glassmorphism + dark mode nativo**,
tipografia médica legível, mobile/tablet-first, alto contraste e micro-interações suaves.
Os tokens abaixo estão implementados em código em [`app/lib/theme/`](../app/lib/theme).

---

## 1. Princípios visuais

1. **Clareza clínica primeiro** — nenhum enfeite compete com o dado clínico. Números vitais
   grandes, hierarquia forte, densidade calibrada para beira-leito.
2. **Glass sobre profundidade** — camadas translúcidas (blur) sobre um fundo com gradiente
   sutil dão profundidade sem ruído. Vidro é para *containers*, nunca para texto de leitura longa.
3. **Dark-first, light impecável** — o tema escuro é o padrão (plantão/sala escura); o claro é
   igualmente polido. Alternância automática (sistema) + manual + modo alto contraste.
4. **2 cliques** — toda ação frequente alcançável em ≤2 toques; FAB contextual e comandos rápidos.
5. **Feedback imediato** — cada toque responde em <100 ms (ripple/scale); estados de carregamento
   com *skeleton*, nunca telas brancas.
6. **Acessibilidade** — contraste mínimo WCAG AA (AAA no modo alto contraste), alvos ≥48 dp,
   suporte a leitor de tela e escala de fonte do sistema.

---

## 2. Tokens de cor

Paleta semântica (não usar cores cruas na UI — sempre via token). Cor de marca: **teal/azul
clínico** (confiança + saúde), com acentos funcionais.

### 2.1 Marca e acento
| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| `brand/primary` | `#0E7C86` | `#22D3C5` | Ações primárias, marca |
| `brand/primaryContainer` | `#CFF5F1` | `#0B4A50` | Fundo de ênfase |
| `accent/secondary` | `#4F6BED` | `#8AA0FF` | Links, seleção |

### 2.2 Superfícies (base do glass)
| Token | Light | Dark |
|-------|-------|------|
| `bg/base` | `#F4F7F9` | `#0A0F14` |
| `bg/gradientTop` | `#EAF3F5` | `#0C1620` |
| `bg/gradientBottom` | `#F7FAFB` | `#0A0F14` |
| `surface/glass` | `rgba(255,255,255,0.55)` | `rgba(22,32,42,0.55)` |
| `surface/glassStroke` | `rgba(255,255,255,0.65)` | `rgba(255,255,255,0.08)` |
| `surface/card` | `#FFFFFF` | `#121A22` |

### 2.3 Semânticas clínicas (estados/alertas)
| Token | Cor | Significado |
|-------|-----|-------------|
| `status/ok` | `#1FA971` | Dentro da meta (verde) |
| `status/warn` | `#E0A500` | Atenção / limítrofe (âmbar) |
| `status/critical` | `#E5484D` | Crítico / fora de faixa (vermelho) |
| `status/info` | `#4F6BED` | Informativo |
| `clin/anemia` | `#C2410C` | Série Hb/ferro |
| `clin/dmo` | `#7C3AED` | Série PTH/Ca/P |
| `clin/adequacy` | `#0E7C86` | Kt/V, adequação |

> **Regra de daltonismo:** cor nunca é o único sinal — sempre acompanha ícone + rótulo
> (ex.: seta ▲/▼ e o valor de referência).

### 2.4 Texto
| Token | Light | Dark |
|-------|-------|------|
| `text/primary` | `#0B1620` | `#EAF2F5` |
| `text/secondary` | `#48606E` | `#9DB2BE` |
| `text/onBrand` | `#FFFFFF` | `#04211F` |

---

## 3. Tipografia

Família: **Inter** (UI) + **IBM Plex Mono** (números clínicos/doses/laboratório — tabular).
Motivo: alta legibilidade em telas pequenas, numerais tabulares (colunas de exames alinham).

| Token | Tamanho / peso | Uso |
|-------|----------------|-----|
| `display` | 32 / 700 | Números vitais grandes (peso, PA) |
| `titleL` | 22 / 600 | Título de tela |
| `titleM` | 18 / 600 | Cabeçalho de card |
| `body` | 15 / 400 | Texto padrão |
| `label` | 13 / 500 | Rótulos, chips |
| `caption` | 12 / 400 | Metadados, timestamps |
| `mono` | 15 / 500 (tabular) | Doses, resultados, Kt/V |

Escala de fonte respeita `MediaQuery.textScaler` (acessibilidade).

---

## 4. Espaçamento, raio e elevação

- **Grid base 4 dp.** Espaços: `4, 8, 12, 16, 20, 24, 32, 40`.
- **Raio:** `sm 8 · md 12 · lg 16 · xl 24 · pill 999`. Cards de vidro usam `lg`/`xl`.
- **Elevação (dark):** sombra sutil + borda de 1 px `glassStroke` (o brilho da borda define
  profundidade melhor que sombra no escuro).
- **Blur do vidro:** `sigma 18–24` no fundo, com `saturation` +10% para vivacidade.

---

## 5. Componentes-núcleo (reutilizáveis)

| Componente | Descrição |
|------------|-----------|
| `GlassCard` | Container translúcido (blur + borda + gradiente) — base de quase tudo |
| `GlassScaffold` | Scaffold com fundo em gradiente + camada de blur |
| `VitalTile` | Número clínico grande + rótulo + tendência (▲/▼) + cor semântica |
| `TrendChart` | Gráfico de linha (fl_chart) com faixa-meta sombreada e pontos fora-de-faixa |
| `StatusPill` | Chip de status clínico (ok/warn/critical) com ícone |
| `AlertBanner` | Faixa de alerta proativo (meta de anemia, exame faltando no LME) |
| `QuickActionBar` | Barra de ações rápidas contextuais (2 cliques) |
| `TimelineItem` | Item da linha do tempo unificada (consulta/HD/exame/evolução) |
| `SoapEditor` | Editor SOAP estruturado + campo IA ("Sumarizar") |
| `NumericKeypadField` | Campo com teclado numérico grande (beira-leito) |
| `SignatureBar` | Barra de assinatura (step-up auth) para fechar documento |

Todos: estados `default/hover/pressed/focus/disabled/loading`, acessíveis, testáveis.

---

## 6. Movimento e micro-interações

- **Duração:** `fast 120ms · base 200ms · slow 320ms`; curva padrão `easeOutCubic`.
- Toque: *scale* 0.98 + ripple. Aparição de card: *fade + slide up 8dp*.
- Transição de tela: *shared axis* (horizontal entre abas, vertical em push).
- Atualização de valor vital: *count-up* curto + flash da cor de status.
- **Reduza movimento** quando `MediaQuery.disableAnimations` (acessibilidade).

---

## 7. Dashboards por perfil (resumo)

| Perfil | Foco do dashboard |
|--------|-------------------|
| **Médico** | Pacientes do dia, alertas clínicos (anemia/DMO), LMEs a vencer, pendências de assinatura |
| **Enfermeiro** | Mapa da sala de HD, eMAR pendente, recepções, SAE do turno |
| **Técnico** | Sessões atribuídas, parâmetros a registrar, checklist de máquina |
| **Administrativo** | Agenda/escala, faturamento, pendências documentais, censo |

---

## 8. Ícones e ilustração

- Ícones em traço 1.75 px (linha), família consistente (Lucide/Material Symbols outlined).
- Ilustrações de estado vazio discretas, monocromáticas na cor de marca.
- Ícones clínicos dedicados: acesso vascular, dialisador, gota (fluxo), rim (marca).

---

## 9. Aplicação do glass (regras)

1. Vidro **só em containers** com conteúdo curto/estruturado (cards, barras, modais).
2. **Texto de leitura longa** vai em `surface/card` sólido (contraste e conforto).
3. Máximo de **2 camadas de vidro** sobrepostas (evita "sopa" visual).
4. Sempre há **contraste garantido** por trás do texto (fallback sólido se blur indisponível).
