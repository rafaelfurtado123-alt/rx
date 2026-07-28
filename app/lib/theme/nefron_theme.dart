import 'package:flutter/material.dart';

import 'nefron_colors.dart';
import 'nefron_spacing.dart';
import 'nefron_typography.dart';

/// Montagem dos [ThemeData] claro e escuro do Design System `néfron·`.
///
/// O tema escuro é o padrão do produto. Ambos expõem os tokens semânticos via
/// a [ThemeExtension] [NefronColors], acessível por `context.colors`.
abstract final class NefronTheme {
  static ThemeData light() => _build(Brightness.light, NefronColors.light);
  static ThemeData dark() => _build(Brightness.dark, NefronColors.dark);

  static ThemeData _build(Brightness brightness, NefronColors c) {
    final scheme = ColorScheme.fromSeed(
      seedColor: c.primary,
      brightness: brightness,
      primary: c.primary,
      secondary: c.secondary,
      surface: c.card,
      error: c.critical,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: c.bgGradientBottom,
      fontFamily: 'IBMPlexSans',
      textTheme: NefronType.textTheme(c.textPrimary, c.textSecondary),
      extensions: [c],
      splashFactory: InkSparkle.splashFactory,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(kMinTouchTarget),
          shape: const RoundedRectangleBorder(borderRadius: Radii.rMd),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: c.card.withValues(alpha: 0.6),
        border: const OutlineInputBorder(
          borderRadius: Radii.rMd,
          borderSide: BorderSide.none,
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: Gap.lg, vertical: Gap.md),
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: Radii.rMd),
      ),
    );
  }
}
