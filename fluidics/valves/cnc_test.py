import cnc_talk
cnc = cnc_talk.MockCNC()
plate = cnc_talk.Plate(cnc)
plate.record_well()
cnc.set((8, 12, 0))
plate.record_well(8, 12)
cnc.set((8, 12, 20))
plate.record_height()
plate.freeze()
cnc.set((4, 4, 0))
plate.record_well(4,4)
cnc.set((0, 12, 0))
plate.record_well(0, 12)
cnc.set((8, 0, 0))
plate.record_well(8, 0)
plate.freeze()
