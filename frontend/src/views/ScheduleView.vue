<script setup lang="ts">
import {
  BookingCalendarView,
  DateFormatStrings,
  DEFAULT_SLOT_DURATION,
  EventLocationType,
  MeetingLinkProviderType,
} from '@/definitions';
import {
  ref, inject, computed, onMounted,
} from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { dayjsKey, callKey, refreshKey } from '@/keys';
import {
  RemoteEvent,
  RemoteEventListResponse,
  Schedule,
  ScheduleListResponse,
  ScheduleAppointment,
  TimeFormatted,
} from '@/models';
import ScheduleCreation from '@/components/ScheduleCreation.vue';
import CalendarQalendar from '@/components/CalendarQalendar.vue';

// stores
import { useAppointmentStore } from '@/stores/appointment-store';
import { useCalendarStore } from '@/stores/calendar-store';

const { t } = useI18n();
const route = useRoute();
const dj = inject(dayjsKey);
const call = inject(callKey);
const refresh = inject(refreshKey);

const appointmentStore = useAppointmentStore();
const calendarStore = useCalendarStore();
const { pendingAppointments } = storeToRefs(appointmentStore);
const { connectedCalendars } = storeToRefs(calendarStore);

// current selected date, if not in route: defaults to now
const activeDate = ref(route.params.date ? dj(route.params.date as string) : dj());
const activeDateRange = ref({
  start: activeDate.value.startOf('month'),
  end: activeDate.value.endOf('month'),
});

// active menu item for tab navigation of calendar views
const tabActive = ref(BookingCalendarView.Month);

// get remote calendar data for current year
const calendarEvents = ref<RemoteEvent[]>([]);
const getRemoteEvents = async (from: string, to: string) => {
  // Most calendar impl are non-inclusive of the last day, so just add one to the day.
  const inclusiveTo = dj(to).add(1, 'day').format('YYYY-MM-DD');

  calendarEvents.value = [];
  await Promise.all(connectedCalendars.value.map(async (calendar) => {
    const { data }: RemoteEventListResponse = await call(`rmt/cal/${calendar.id}/${from}/${inclusiveTo}`).get().json();
    if (Array.isArray(data.value)) {
      calendarEvents.value.push(
        ...data.value.map((event) => ({
          ...event,
          duration: dj(event.end).diff(dj(event.start), 'minutes'),
        })),
      );
    }
  }));
};

// user configured schedules from db (only the first for now, later multiple schedules will be available)
const schedules = ref<Schedule[]>([]);
const firstSchedule = computed(() => (schedules.value?.length > 0 ? schedules.value[0] : null));
const schedulesReady = ref(false);
const getFirstSchedule = async () => {
  // trailing slash to prevent fast api redirect which doesn't work great on our container setup
  const { data }: ScheduleListResponse = await call('schedule/').get().json();
  schedules.value = data.value;
};

// schedule previews for showing corresponding placeholders in calendar views
const schedulesPreviews = ref([]);
const schedulePreview = (schedule: ScheduleAppointment) => {
  schedulesPreviews.value = schedule ? [schedule] : [];
};

/**
 * Retrieve new events if a user navigates to a different month
 * @param dateObj
 */
const onDateChange = (dateObj: TimeFormatted) => {
  const start = dj(dateObj.start);
  const end = dj(dateObj.end);

  activeDate.value = start.add(end.diff(start, 'minutes') / 2, 'minutes');

  // remote data is retrieved per month, so a data request happens as soon as the user navigates to a different month
  if (
    dj(activeDateRange.value.end).format('YYYYMM') !== dj(end).format('YYYYMM')
    || dj(activeDateRange.value.start).format('YYYYMM') !== dj(start).format('YYYYMM')
  ) {
    getRemoteEvents(
      dj(start).format('YYYY-MM-DD'),
      dj(end).format('YYYY-MM-DD'),
    );
  }
};

// initially load data when component gets remounted
onMounted(async () => {
  // Don't actually load anything during the FTUE
  if (route.name === 'setup') {
    // Setup a fake schedule so the schedule creation bar works correctly...
    schedules.value = [{
      active: false,
      name: '',
      calendar_id: 0,
      location_type: EventLocationType.InPerson,
      location_url: '',
      details: '',
      start_date: dj().format(DateFormatStrings.QalendarFullDay),
      end_date: null,
      start_time: '09:00',
      end_time: '17:00',
      earliest_booking: 1440,
      farthest_booking: 20160,
      weekdays: [1, 2, 3, 4, 5],
      slot_duration: DEFAULT_SLOT_DURATION,
      meeting_link_provider: MeetingLinkProviderType.None,
      booking_confirmation: true,
      calendar: {
        id: 0,
        title: '',
        color: '#000',
        connected: true,
      },
    }];
    schedulesReady.value = true;
    return;
  }
  await refresh();
  await getFirstSchedule();
  schedulesReady.value = true;
  const eventsFrom = dj(activeDate.value).startOf('month').format('YYYY-MM-DD');
  const eventsTo = dj(activeDate.value).endOf('month').format('YYYY-MM-DD');
  await getRemoteEvents(eventsFrom, eventsTo);
});
</script>

<template>
  <!-- page title area -->
  <div class="flex select-none flex-col items-start justify-between lg:flex-row">
    <div class="text-4xl font-light">{{ t('label.dashboard') }}</div>
  </div>
  <!-- page content -->
  <div
    class="mt-8 flex flex-col-reverse items-stretch gap-2 md:flex-row-reverse lg:gap-4"
    :class="{ 'lg:mt-10': tabActive === BookingCalendarView.Month }"
  >
    <!-- schedule creation dialog -->
    <div class="mx-auto mb-10 w-3/4 min-w-80 sm:w-1/4 md:mb-0 xl:w-1/6">
      <schedule-creation
        v-if="schedulesReady"
        :calendars="connectedCalendars"
        :schedule="firstSchedule"
        :active-date="activeDate"
        @created="getFirstSchedule"
        @updated="schedulePreview"
      />
    </div>
    <!-- main section: big calendar showing active month, week or day -->
    <calendar-qalendar
      class="w-full md:w-9/12 xl:w-10/12"
      :selected="activeDate"
      :appointments="pendingAppointments"
      :events="calendarEvents"
      :schedules="schedulesPreviews"
      @date-change="onDateChange"
    />
  </div>
</template>
