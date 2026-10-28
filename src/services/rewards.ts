/**
 * Future-ready seam for rewarded ads. No advertising SDK is included, so the
 * default provider reports nothing as available and the UI shows no ad
 * buttons. To add ads later, implement RewardedAdProvider with a real SDK,
 * register it with setRewardProvider(), and grant rewards only when show()
 * resolves with granted: true from the SDK's own reward callback.
 */
export type RewardKind = 'extraHint' | 'extraLife' | 'bonusCoins';

export interface RewardedAdProvider {
  readonly id: string;
  isAvailable(kind: RewardKind): boolean;
  show(kind: RewardKind): Promise<{ granted: boolean }>;
  /** Whether a paid "Remove Ads" option exists. */
  readonly removeAdsAvailable: boolean;
}

const NO_ADS: RewardedAdProvider = {
  id: 'none',
  isAvailable: () => false,
  show: async () => ({ granted: false }),
  removeAdsAvailable: false,
};

let provider: RewardedAdProvider = NO_ADS;

export function getRewardProvider(): RewardedAdProvider {
  return provider;
}

export function setRewardProvider(next: RewardedAdProvider | null): void {
  provider = next ?? NO_ADS;
}
