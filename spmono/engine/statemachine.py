"""Tiny state machine: named states with time-in-state tracking."""


class StateMachine:
    def __init__(self, initial):
        self.state = initial
        self.time_in_state = 0

    def set(self, state):
        if state != self.state:
            self.state = state
            self.time_in_state = 0

    def update(self, delta_ms):
        self.time_in_state += delta_ms

    def is_(self, state):
        return self.state == state
