# Néfron — App (Flutter)

Frontend do Prontuário Eletrônico Nefrológico. Web + iOS + Android + tablet, com o
Design System `néfron·` (glassmorphism, dark-first, Material 3).

## Estrutura

```
app/
├── pubspec.yaml
├── analysis_options.yaml
└── lib/
    ├── main.dart              # entrada + vitrine do Design System (temporária)
    ├── theme/                 # tokens e temas (theme.dart = barrel)
    │   ├── nefron_colors.dart      # cores semânticas (light/dark) via ThemeExtension
    │   ├── nefron_typography.dart  # Inter (UI) + IBM Plex Mono (números clínicos)
    │   ├── nefron_spacing.dart     # grid 4dp, raios, blur, motion
    │   └── nefron_theme.dart       # ThemeData claro/escuro
    └── widgets/               # componentes reutilizáveis (widgets.dart = barrel)
        ├── glass_card.dart
        ├── glass_scaffold.dart
        ├── status_pill.dart
        └── vital_tile.dart
```

## Como rodar (localmente)

```bash
cd app
flutter pub get
flutter run -d chrome     # ou -d <device>
```

> Este ambiente remoto não possui o SDK Flutter; o código foi escrito para
> `flutter pub get` / `flutter run` em máquina local.

## Convenções

- Cores sempre via token: `context.colors.primary` (nunca `Color(0x...)` na UI).
- Números clínicos com `NefronType.mono(...)` (tabular, alinham em colunas).
- Vidro só em containers curtos; leitura longa em `context.colors.card`.
- Acessibilidade: alvos ≥48 dp, cor + ícone + rótulo, respeito a `disableAnimations`.

## Próximas etapas

3. Autenticação (login + 2FA) + Dashboard por perfil (go_router + Riverpod + Supabase)
4. Prontuário + Evolução · 5. Prescrição de HD · 6. LME Inteligente
