import { create } from 'zustand';

interface IntentState {
  isVerified: boolean;
  setVerified: (val: boolean) => void;
}

export const useIntentStore = create<IntentState>((set) => ({
  isVerified: false,
  setVerified: (val) => set({ isVerified: val }),
}));
