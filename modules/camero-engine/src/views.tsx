import { requireNativeView } from 'expo';
import * as React from 'react';

import type { CameroCameraViewProps, CameroCanvasViewProps } from './types';

const NativeCameraView: React.ComponentType<CameroCameraViewProps> = requireNativeView('CameroCamera');
const NativeCanvasView: React.ComponentType<CameroCanvasViewProps> = requireNativeView('CameroCanvas');

export function CameraView(props: CameroCameraViewProps) {
  return <NativeCameraView {...props} />;
}

export function CanvasView(props: CameroCanvasViewProps) {
  return <NativeCanvasView {...props} />;
}
