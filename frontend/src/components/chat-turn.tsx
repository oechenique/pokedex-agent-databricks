import type { ConversationTurn } from "@/lib/types";
import PokemonCard from "./pokemon-card";
import CompareTable from "./compare-table";
import TypeMatchupBadges from "./type-matchups";
import OakText from "./oak-text";
import styles from "./chat-turn.module.css";

export default function ChatTurn({ turn }: { turn: ConversationTurn }) {
  if (turn.role === "user") {
    return (
      <div className={`${styles.row} ${styles.userRow}`}>
        <div className={styles.userBubble}>{turn.content as string}</div>
      </div>
    );
  }

  const content = turn.content;
  if (typeof content === "string") {
    return null;
  }

  return (
    <div className={styles.row}>
      <div className={styles.avatar} aria-hidden="true">
        🔬
      </div>
      <div className={styles.oakContent}>
        {content.kind === "text" && (
          <div className={styles.oakBubble}>
            <OakText text={content.text} />
          </div>
        )}

        {content.kind === "pokemon" && (
          <>
            <PokemonCard pokemon={content.pokemon} />
            {content.text && (
              <div className={`${styles.oakBubble} ${styles.followUp}`}>
                <OakText text={content.text} />
              </div>
            )}
          </>
        )}

        {content.kind === "compare" && (
          <>
            <CompareTable compare={content.compare} />
            {content.text && (
              <div className={`${styles.oakBubble} ${styles.followUp}`}>
                <OakText text={content.text} />
              </div>
            )}
          </>
        )}

        {content.kind === "matchups" && (
          <>
            <TypeMatchupBadges matchups={content.matchups} />
            {content.text && (
              <div className={`${styles.oakBubble} ${styles.followUp}`}>
                <OakText text={content.text} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
