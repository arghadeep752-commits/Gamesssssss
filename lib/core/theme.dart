import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Hime design tokens.
class HimeColors {
  static const yellow = Color(0xFFF5D547);
  static const yellowDeep = Color(0xFFE2BC1F);
  static const yellowSoft = Color(0xFFFFF6CC);
  static const ink = Color(0xFF202124);
  static const inkSoft = Color(0xFF3C4043);
  static const muted = Color(0xFF777777);
  static const background = Color(0xFFFAFAFA);
  static const surface = Color(0xFFFFFFFF);
  static const border = Color(0xFFEEEEEE);
  static const online = Color(0xFF2EB872);
  static const danger = Color(0xFFD93F3F);
  static const read = Color(0xFF2F80ED);

  // Dark theme
  static const darkBackground = Color(0xFF111214);
  static const darkSurface = Color(0xFF1B1C1F);
  static const darkSurfaceHigh = Color(0xFF26272B);
  static const darkBorder = Color(0xFF2E3034);
  static const darkText = Color(0xFFECEDEF);
  static const darkMuted = Color(0xFF9A9CA1);
}

/// Edge-to-edge system bars: the status bar and the navigation bar are fully
/// transparent, so the app's own colours run to the edges of the screen (no
/// grey band behind the clock and battery, no black strip behind the
/// navigation buttons). Icons switch between dark and light with the theme.
class HimeSystemUi {
  static SystemUiOverlayStyle of({required bool dark}) => SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: dark ? Brightness.light : Brightness.dark,
        statusBarBrightness: dark ? Brightness.dark : Brightness.light,
        systemStatusBarContrastEnforced: false,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarDividerColor: Colors.transparent,
        systemNavigationBarIconBrightness: dark ? Brightness.light : Brightness.dark,
        systemNavigationBarContrastEnforced: false,
      );

  /// For full-bleed dark screens (calls, status viewer, photo/video preview).
  static final onDark = of(dark: true);
}

/// Quick WhatsApp-style slide: the new screen comes in from the right while
/// the old one moves a little to the left. Transforms only (no full-screen
/// fades), which keeps navigation smooth on low-end phones.
Widget himeSlideTransition(Animation<double> animation, Animation<double> secondaryAnimation, Widget child) {
  final enter = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic, reverseCurve: Curves.easeInCubic);
  final exit = CurvedAnimation(parent: secondaryAnimation, curve: Curves.easeOutCubic, reverseCurve: Curves.easeInCubic);
  return SlideTransition(
    position: Tween<Offset>(begin: Offset.zero, end: const Offset(-0.2, 0)).animate(exit),
    child: SlideTransition(
      position: Tween<Offset>(begin: const Offset(1, 0), end: Offset.zero).animate(enter),
      child: child,
    ),
  );
}

class HimePageTransitionsBuilder extends PageTransitionsBuilder {
  const HimePageTransitionsBuilder();

  @override
  Widget buildTransitions<T>(PageRoute<T> route, BuildContext context, Animation<double> animation,
          Animation<double> secondaryAnimation, Widget child) =>
      himeSlideTransition(animation, secondaryAnimation, child);
}

class HimeSpace {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 24.0;
  static const xxl = 32.0;
}

class HimeRadius {
  static const sm = 10.0;
  static const md = 14.0;
  static const lg = 20.0;
  static const bubble = 18.0;
}

/// Colours that are not part of Material's ColorScheme.
@immutable
class HimePalette extends ThemeExtension<HimePalette> {
  const HimePalette({
    required this.outgoingBubble,
    required this.onOutgoingBubble,
    required this.incomingBubble,
    required this.onIncomingBubble,
    required this.muted,
    required this.border,
    required this.chatBackground,
    required this.skeleton,
  });

  final Color outgoingBubble;
  final Color onOutgoingBubble;
  final Color incomingBubble;
  final Color onIncomingBubble;
  final Color muted;
  final Color border;
  final Color chatBackground;
  final Color skeleton;

  static const light = HimePalette(
    outgoingBubble: Color(0xFFFFF1B0),
    onOutgoingBubble: HimeColors.ink,
    incomingBubble: Colors.white,
    onIncomingBubble: HimeColors.ink,
    muted: HimeColors.muted,
    border: HimeColors.border,
    chatBackground: Color(0xFFF6F4EE),
    skeleton: Color(0xFFEDEDED),
  );

  static const dark = HimePalette(
    outgoingBubble: Color(0xFF4A4220),
    onOutgoingBubble: HimeColors.darkText,
    incomingBubble: HimeColors.darkSurfaceHigh,
    onIncomingBubble: HimeColors.darkText,
    muted: HimeColors.darkMuted,
    border: HimeColors.darkBorder,
    chatBackground: Color(0xFF0D0E10),
    skeleton: Color(0xFF2A2B2F),
  );

  @override
  HimePalette copyWith() => this;

  @override
  HimePalette lerp(ThemeExtension<HimePalette>? other, double t) => t < 0.5 ? this : (other as HimePalette? ?? this);
}

extension HimeThemeX on BuildContext {
  HimePalette get palette => Theme.of(this).extension<HimePalette>() ?? HimePalette.light;
  ColorScheme get colors => Theme.of(this).colorScheme;
  TextTheme get text => Theme.of(this).textTheme;
  bool get isDark => Theme.of(this).brightness == Brightness.dark;
}

class HimeTheme {
  static const _display = 'Poppins';

  static TextTheme _text(Color body, Color muted) {
    final base = Typography.material2021().black;
    TextStyle? d(TextStyle? s, double size, FontWeight w, {double? h}) =>
        s?.copyWith(fontFamily: _display, fontSize: size, fontWeight: w, height: h, color: body, letterSpacing: -0.2);
    TextStyle? b(TextStyle? s, double size, FontWeight w, {Color? c, double? h}) =>
        s?.copyWith(fontSize: size, fontWeight: w, color: c ?? body, height: h, letterSpacing: 0.1);
    return base.copyWith(
      displaySmall: d(base.displaySmall, 32, FontWeight.w700, h: 1.15),
      headlineMedium: d(base.headlineMedium, 26, FontWeight.w700, h: 1.2),
      headlineSmall: d(base.headlineSmall, 22, FontWeight.w600, h: 1.25),
      titleLarge: d(base.titleLarge, 20, FontWeight.w600),
      titleMedium: b(base.titleMedium, 16, FontWeight.w600),
      titleSmall: b(base.titleSmall, 14, FontWeight.w600),
      bodyLarge: b(base.bodyLarge, 16, FontWeight.w400, h: 1.35),
      bodyMedium: b(base.bodyMedium, 14.5, FontWeight.w400, h: 1.35),
      bodySmall: b(base.bodySmall, 12.5, FontWeight.w400, c: muted),
      labelLarge: b(base.labelLarge, 15, FontWeight.w600),
      labelMedium: b(base.labelMedium, 12.5, FontWeight.w500, c: muted),
      labelSmall: b(base.labelSmall, 11, FontWeight.w500, c: muted),
    );
  }

  static ThemeData light() {
    const scheme = ColorScheme(
      brightness: Brightness.light,
      primary: HimeColors.yellow,
      onPrimary: HimeColors.ink,
      primaryContainer: HimeColors.yellowSoft,
      onPrimaryContainer: HimeColors.ink,
      secondary: HimeColors.ink,
      onSecondary: Colors.white,
      error: HimeColors.danger,
      onError: Colors.white,
      surface: HimeColors.surface,
      onSurface: HimeColors.ink,
      surfaceContainerLowest: Colors.white,
      surfaceContainerLow: HimeColors.background,
      surfaceContainer: Color(0xFFF3F3F3),
      surfaceContainerHigh: Color(0xFFEDEDED),
      surfaceContainerHighest: Color(0xFFE6E6E6),
      onSurfaceVariant: HimeColors.muted,
      outline: Color(0xFFDDDDDD),
      outlineVariant: HimeColors.border,
    );
    return _build(scheme, HimePalette.light, HimeColors.background, HimeColors.muted);
  }

  static ThemeData dark() {
    const scheme = ColorScheme(
      brightness: Brightness.dark,
      primary: HimeColors.yellow,
      onPrimary: HimeColors.ink,
      primaryContainer: Color(0xFF3D3615),
      onPrimaryContainer: HimeColors.yellow,
      secondary: HimeColors.darkText,
      onSecondary: HimeColors.ink,
      error: Color(0xFFFF6B6B),
      onError: HimeColors.ink,
      surface: HimeColors.darkSurface,
      onSurface: HimeColors.darkText,
      surfaceContainerLowest: HimeColors.darkBackground,
      surfaceContainerLow: HimeColors.darkBackground,
      surfaceContainer: HimeColors.darkSurfaceHigh,
      surfaceContainerHigh: Color(0xFF2D2E33),
      surfaceContainerHighest: Color(0xFF34363B),
      onSurfaceVariant: HimeColors.darkMuted,
      outline: Color(0xFF3A3C41),
      outlineVariant: HimeColors.darkBorder,
    );
    return _build(scheme, HimePalette.dark, HimeColors.darkBackground, HimeColors.darkMuted);
  }

  static ThemeData _build(ColorScheme scheme, HimePalette palette, Color background, Color muted) {
    final text = _text(scheme.onSurface, muted);
    final dark = scheme.brightness == Brightness.dark;
    final fieldFill = dark ? HimeColors.darkSurfaceHigh : const Color(0xFFF4F4F4);
    final radius = BorderRadius.circular(HimeRadius.md);
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: scheme.brightness,
      scaffoldBackgroundColor: background,
      canvasColor: background,
      textTheme: text,
      // InkRipple is much lighter than the shader-based InkSparkle on
      // budget phones, so taps feel instant.
      splashFactory: InkRipple.splashFactory,
      visualDensity: VisualDensity.standard,
      extensions: [palette],
      dividerTheme: DividerThemeData(color: palette.border, thickness: 1, space: 1),
      appBarTheme: AppBarThemeData(
        backgroundColor: background,
        foregroundColor: scheme.onSurface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: false,
        titleTextStyle: text.titleLarge,
        systemOverlayStyle: HimeSystemUi.of(dark: dark),
      ),
      inputDecorationTheme: InputDecorationThemeData(
        filled: true,
        fillColor: fieldFill,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        hintStyle: text.bodyMedium?.copyWith(color: muted),
        labelStyle: text.bodyMedium?.copyWith(color: muted),
        border: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide.none),
        enabledBorder: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: const BorderSide(color: HimeColors.yellowDeep, width: 1.4),
        ),
        errorBorder: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: scheme.error)),
        focusedErrorBorder: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: scheme.error, width: 1.4)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: HimeColors.yellow,
          foregroundColor: HimeColors.ink,
          disabledBackgroundColor: HimeColors.yellow.withValues(alpha: 0.45),
          disabledForegroundColor: HimeColors.ink.withValues(alpha: 0.5),
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: text.labelLarge,
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: scheme.onSurface,
          minimumSize: const Size.fromHeight(52),
          side: BorderSide(color: scheme.outline),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: text.labelLarge,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: dark ? HimeColors.yellow : HimeColors.ink,
          textStyle: text.labelLarge,
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: HimeColors.yellow,
        foregroundColor: HimeColors.ink,
        elevation: 2,
        shape: StadiumBorder(),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        showDragHandle: true,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(HimeRadius.lg)),
        titleTextStyle: text.titleLarge,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: dark ? HimeColors.darkSurfaceHigh : HimeColors.ink,
        contentTextStyle: text.bodyMedium?.copyWith(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      listTileTheme: ListTileThemeData(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        iconColor: scheme.onSurface,
        titleTextStyle: text.titleSmall?.copyWith(fontSize: 15.5),
        subtitleTextStyle: text.bodySmall,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? HimeColors.ink : null),
        trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? HimeColors.yellow : null),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: HimeColors.yellowDeep),
      chipTheme: ChipThemeData(
        backgroundColor: fieldFill,
        selectedColor: HimeColors.yellow,
        labelStyle: text.labelMedium?.copyWith(color: scheme.onSurface),
        side: BorderSide.none,
        shape: const StadiumBorder(),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      pageTransitionsTheme: const PageTransitionsTheme(builders: {
        TargetPlatform.android: HimePageTransitionsBuilder(),
        TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
      }),
    );
  }
}
