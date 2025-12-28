declare module '@js-temporal/polyfill' {
  export namespace Temporal {
    interface PlainDate {
      year: number;
      month: number;
      day: number;
      /** ISO day of week: Monday = 1 .. Sunday = 7 */
      dayOfWeek: number;
      toString(): string;
    }

    interface PlainTime {
      hour: number;
      minute: number;
      second: number;
      millisecond: number;
      microsecond: number;
      nanosecond: number;
    }

    interface ZonedDateTime {
      epochNanoseconds: bigint;
      epochMilliseconds: number;
      add(duration: { days?: number }): ZonedDateTime;
    }

    interface Instant {
      toZonedDateTimeISO(timeZone: string): ZonedDateTime;
    }

    interface TimeZoneLike {
      id: string;
    }

    const PlainDate: {
      from(isoString: string): PlainDate;
    };

    const PlainTime: {
      from(isoString: string): PlainTime;
    };

    const ZonedDateTime: {
      from(options: {
        timeZone: string;
        year: number;
        month: number;
        day: number;
        hour: number;
        minute?: number;
        second?: number;
        millisecond?: number;
        microsecond?: number;
        nanosecond?: number;
      }): ZonedDateTime;
      compare(a: ZonedDateTime, b: ZonedDateTime): number;
    };

    const Instant: {
      from(isoString: string): Instant;
      compare(a: Instant, b: Instant): number;
    };

    const TimeZone: {
      from(timeZone: string): TimeZoneLike;
    };
  }

  export const Temporal: typeof Temporal;
}
