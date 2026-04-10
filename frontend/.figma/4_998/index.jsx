import React from 'react';

import styles from './index.module.scss';

const Component = () => {
  return (
    <div className={styles.calendarYearField}>
      <div className={styles.select}>
        <p className={styles.a2025}>国家/地区</p>
        <img src="../image/mnivt7vg-87w7fv1.svg" className={styles.chevronDown} />
      </div>
    </div>
  );
}

export default Component;
