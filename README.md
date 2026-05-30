# Last Hit Trainer / 补刀训练器

一个小型 MOBA 风格 Pygame demo。你控制红色英雄，对抗一个蓝色 CPU，目标很简单：**补刀、赚钱、别让小兵和塔抢走你的金币。**

A small MOBA-style Pygame demo. You control the red hero against a blue CPU. The goal is simple: **last-hit minions, earn gold, and do not let minions or towers steal your money.**

## How to Run / 如何运行

Install Pygame first:

```bash
pip install pygame
```

Then run:

```bash
python last_hit_trainer.py
```

## Controls / 操作方式

你控制的是红色英雄。

You control the red hero.

| Action / 动作 | Key / 按键 |
| --- | --- |
| Move / 移动 | Arrow keys / 方向键 |
| Attack / 攻击 | Enter |
| Restart / 重开 | R |
| Quit / 退出 | Esc |

蓝色英雄不需要你操作。

The blue hero is controlled by the CPU.

## Goal / 游戏目标

在 60 秒内获得尽可能多的金币。只有你打出最后一击时，才会获得金币。

Earn as much gold as possible in 60 seconds. You only get gold if your attack is the final hit.

You get gold when:

- You kill a blue minion with the red hero.
- The floating text shows something like `Player +20`.



## CPU Behavior / CPU 行为

蓝色 CPU 会自动寻找补刀机会，但它不是完美的。它大约只有 25% 的概率抓住补刀机会，也就是说它会漏掉大约 75% 的补刀。

The blue CPU looks for last-hit chances automatically, but it is not perfect. It only takes about 25% of its chances, so it misses around 75%.

This is controlled in the code by:

```python
blue_ai_last_hit_chance = 0.25
```

如果你想让 CPU 更强，可以把它调高，比如 `0.40`。如果你想让 CPU 更菜，可以调低，比如 `0.10`。

To make the CPU stronger, increase it, for example `0.40`. To make the CPU weaker, lower it, for example `0.10`.


## Win Condition / 怎么算赢

没有复杂规则，最后看金币的数量：

No complicated rule. Just compare gold:

祝你补刀顺利。不要让塔拿走你的工资。

Good luck. Do not let the tower take your salary.
