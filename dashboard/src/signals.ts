import type { Family, LampSignal } from './data.ts';

export const FAM: Record<Family, readonly (readonly [LampSignal, string])[]> = {
  bottom: [['vix_high', 'VIX 高'], ['pc_high', 'P/C 高'], ['foreign', '外資賣'], ['margin', '融資減'], ['default', '違約'], ['loss', '畢業文'], ['creative', '創作文']],
  top: [['vix_low', 'VIX 低'], ['pc_low', 'P/C 低'], ['fut_long', '期貨多單'], ['foreign_buy', '外資買'], ['margin_up', '融資增'], ['turnover', '量能'], ['hot_ptt', '過熱文'], ['stretch', '乖離']],
  warn: [['fut_short', '淨空單'], ['fut_ratio_short', '空單佔比'], ['fut_chg_short', '增空單']],
};

export const temperatureLevels = [[0, '平常', '<80'], [80, '留意', '80–85'], [85, '偏恐慌', '85–90'], [90, '恐慌', '90–95'], [95, '極度恐慌', '≥95']] as const;
