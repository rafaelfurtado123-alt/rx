import 'package:flutter/material.dart';

/// Tipografia do Design System `néfron·`.
///
/// IBM Plex Sans para UI e IBM Plex Mono (tabular) para números clínicos —
/// doses, resultados de exames e Kt/V — de modo que colunas numéricas alinhem.
/// As fontes são EMPACOTADAS como assets (pubspec.yaml): nada é buscado em CDN
/// em tempo de execução — requisito de disponibilidade offline e LGPD.
abstract final class NefronType {
  static const String _sans = 'IBMPlexSans';
  static const String _mono = 'IBMPlexMono';

  /// Estilos de texto da UI, tintados com [color].
  static TextTheme textTheme(Color color, Color secondary) {
    TextStyle s(double size, FontWeight weight, Color cor) => TextStyle(
        fontFamily: _sans, fontSize: size, fontWeight: weight, color: cor);
    return TextTheme(
      displaySmall: s(32, FontWeight.w700, color),
      titleLarge: s(22, FontWeight.w600, color),
      titleMedium: s(18, FontWeight.w600, color),
      bodyLarge: s(15, FontWeight.w400, color),
      bodyMedium: s(15, FontWeight.w400, color),
      labelLarge: s(13, FontWeight.w500, color),
      bodySmall: s(12, FontWeight.w400, secondary),
    );
  }

  /// Estilo monoespaçado tabular para números clínicos (doses, exames, Kt/V).
  static TextStyle mono({
    required Color color,
    double size = 15,
    FontWeight weight = FontWeight.w500,
  }) {
    return TextStyle(
      fontFamily: _mono,
      fontSize: size,
      fontWeight: weight,
      color: color,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
  }

  /// Número vital grande (peso, PA), monoespaçado.
  static TextStyle vital(Color color) =>
      mono(color: color, size: 32, weight: FontWeight.w700);
}
