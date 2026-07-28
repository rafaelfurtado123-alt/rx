import 'package:flutter/widgets.dart';

/// Espaçamento e raios do Design System `néfron·` (grid base 4 dp).
abstract final class Gap {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
  static const double huge = 40;
}

/// Raios de canto.
abstract final class Radii {
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double pill = 999;

  static const BorderRadius rSm = BorderRadius.all(Radius.circular(sm));
  static const BorderRadius rMd = BorderRadius.all(Radius.circular(md));
  static const BorderRadius rLg = BorderRadius.all(Radius.circular(lg));
  static const BorderRadius rXl = BorderRadius.all(Radius.circular(xl));
}

/// Parâmetros do efeito de vidro (glassmorphism).
abstract final class Glass {
  static const double blurSigma = 20; // sigma 18–24
  static const double strokeWidth = 1;
}

/// Durações e curvas de movimento.
abstract final class Motion {
  static const Duration fast = Duration(milliseconds: 120);
  static const Duration base = Duration(milliseconds: 200);
  static const Duration slow = Duration(milliseconds: 320);
  static const Curve curve = Curves.easeOutCubic;
}

/// Alvo mínimo de toque (acessibilidade).
const double kMinTouchTarget = 48;
