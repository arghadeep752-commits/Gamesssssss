import { useEvent, useEventListener } from 'expo';
import { Image } from 'expo-image';
import { useVideoPlayer, VideoView } from 'expo-video';
import React, { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

import { Engine } from '../../../modules/camero-engine';
import { formatClock } from '../../lib/format';
import { useAccent } from '../../theme/accent';
import { palette, space } from '../../theme/tokens';
import { Icon } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

const posters = new Map<string, string>();

function usePoster(uri: string): string | null {
  const [poster, setPoster] = useState<string | null>(posters.get(uri) ?? null);
  useEffect(() => {
    if (poster) return;
    let alive = true;
    Engine.getThumbnail(uri, 1024)
      .then((t) => {
        if (!t) return;
        posters.set(uri, t);
        if (alive) setPoster(t);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [uri, poster]);
  return poster;
}

type Props = {
  uri: string;
  width: number;
  height: number;
  active: boolean;
  chrome: boolean;
  bottomInset: number;
  onTap: () => void;
};

/** A video page in the viewer. Only the page on screen holds a player. */
export function VideoPage({ uri, width, height, active, chrome, bottomInset, onTap }: Props) {
  const poster = usePoster(uri);
  if (!active) {
    return (
      <Pressable style={{ width, height }} onPress={onTap}>
        {poster ? <Image source={{ uri: poster }} style={StyleSheet.absoluteFill} contentFit="contain" /> : null}
        <View style={styles.center} pointerEvents="none">
          <View style={styles.bigPlay}>
            <Icon name="play" size={30} />
          </View>
        </View>
      </Pressable>
    );
  }
  return <ActiveVideo uri={uri} width={width} height={height} chrome={chrome} bottomInset={bottomInset} onTap={onTap} />;
}

function ActiveVideo({ uri, width, height, chrome, bottomInset, onTap }: Omit<Props, 'active'>) {
  const accent = useAccent();
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.timeUpdateEventInterval = 0.25;
    p.play();
  });
  const { isPlaying } = useEvent(player, 'playingChange', { isPlaying: player.playing });
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [trackWidth, setTrackWidth] = useState(1);
  const scrubbing = useRef(false);
  const wasPlaying = useRef(false);

  useEventListener(player, 'timeUpdate', (e) => {
    if (!scrubbing.current) setPosition(e.currentTime);
  });
  useEventListener(player, 'sourceLoad', (e) => setDuration(e.duration));
  useEffect(() => {
    player.muted = muted;
  }, [muted, player]);

  const seekTo = (fraction: number, end: boolean) => {
    const d = duration || player.duration || 0;
    const t = Math.max(0, Math.min(d, fraction * d));
    setPosition(t);
    player.currentTime = t;
    if (end) {
      scrubbing.current = false;
      if (wasPlaying.current) player.play();
    }
  };
  const beginScrub = () => {
    scrubbing.current = true;
    wasPlaying.current = player.playing;
    player.pause();
  };

  const scrub = Gesture.Pan()
    .runOnJS(true)
    .minDistance(0)
    .onBegin((e) => {
      beginScrub();
      seekTo(e.x / trackWidth, false);
    })
    .onUpdate((e) => seekTo(e.x / trackWidth, false))
    .onFinalize((e) => seekTo(e.x / trackWidth, true));

  const progress = duration > 0 ? Math.min(1, position / duration) : 0;

  return (
    <View style={{ width, height }}>
      <VideoView player={player} style={StyleSheet.absoluteFill} nativeControls={false} contentFit="contain" surfaceType="textureView" />
      <Pressable style={StyleSheet.absoluteFill} onPress={onTap} />
      {!isPlaying && !scrubbing.current ? (
        <View style={styles.center} pointerEvents="box-none">
          <Tap haptic="light" onPress={() => player.play()} style={styles.bigPlay} accessibilityLabel="Play">
            <Icon name="play" size={30} />
          </Tap>
        </View>
      ) : null}
      {chrome ? (
        <View style={[styles.controls, { bottom: bottomInset }]}>
          <Tap
            haptic="selection"
            onPress={() => (player.playing ? player.pause() : player.play())}
            style={styles.ctrl}
            accessibilityLabel={isPlaying ? 'Pause' : 'Play'}
          >
            <Icon name={isPlaying ? 'pause' : 'play'} size={22} />
          </Tap>
          <T variant="readout" style={styles.time}>
            {formatClock(position * 1000)}
          </T>
          <GestureDetector gesture={scrub}>
            <View style={styles.track} onLayout={(e: LayoutChangeEvent) => setTrackWidth(Math.max(1, e.nativeEvent.layout.width))}>
              <View style={styles.rail} />
              <View style={[styles.played, { width: `${progress * 100}%`, backgroundColor: accent }]} />
              <View style={[styles.knob, { left: progress * trackWidth - 6 }]} />
            </View>
          </GestureDetector>
          <T variant="readout" color={palette.ash} style={styles.time}>
            {formatClock(duration * 1000)}
          </T>
          <Tap haptic="selection" onPress={() => setMuted((m) => !m)} style={styles.ctrl} accessibilityLabel={muted ? 'Turn sound on' : 'Mute'}>
            <Icon name={muted ? 'mute' : 'volume'} size={22} />
          </Tap>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
  bigPlay: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: palette.scrimStrong,
    alignItems: 'center',
    justifyContent: 'center',
    paddingLeft: 3,
  },
  controls: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: space.sm,
    backgroundColor: palette.scrim,
  },
  ctrl: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  time: { minWidth: 44, textAlign: 'center' },
  track: { flex: 1, height: 36, justifyContent: 'center', marginHorizontal: space.xs },
  rail: { position: 'absolute', left: 0, right: 0, height: 2, borderRadius: 1, backgroundColor: palette.rule },
  played: { position: 'absolute', left: 0, height: 2, borderRadius: 1 },
  knob: { position: 'absolute', width: 12, height: 12, borderRadius: 6, backgroundColor: palette.ink },
});
