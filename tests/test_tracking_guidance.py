"""Camera coaching must describe detected issues and preserve mirrored identity."""
import os
import unittest
import numpy as np
from config import Config
from player_manager import PlayerManager,visibility_message
from tracking_types import TrackingFrame,neutral_pose,CORE,LH,RH,LW,RW,NOSE,LA
from ui.tracking_preview import draw_tracking_overlay,labelled_bodies


class VisibilityGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.config=Config()
        self.frame=TrackingFrame(10,neutral_pose(),people=1)

    def test_clipped_feet_explain_distance_without_claiming_lighting_problem(self):
        self.frame.landmarks[LA,1]=1.05
        player=PlayerManager(self.config)
        player.update(self.frame,10)
        self.assertFalse(player.valid)
        self.assertIn("Step back",player.message)
        self.assertIn("feet",player.message)
        self.assertNotIn("lighting",player.message)

    def test_uncertain_hand_is_not_mistaken_for_clipped_whole_body(self):
        self.frame.landmarks[RW,3]=.2
        message=visibility_message(self.frame,10,self.config)
        self.assertIn("hands",message)
        self.assertNotIn("back",message)
        self.assertNotIn("lighting",message)

    def test_uncertain_head_requests_clear_head_view(self):
        self.frame.landmarks[NOSE,3]=.3
        self.assertIn("head",visibility_message(self.frame,10,self.config))

    def test_sideways_clipping_requests_the_actual_direction_in_mirrored_preview(self):
        for x,direction in ((-.03,"RIGHT"),(1.03,"LEFT")):
            with self.subTest(x=x):
                self.frame.landmarks[LH,0]=x
                message=visibility_message(self.frame,10,self.config)
                self.assertIn("Move "+direction,message)
                self.assertIn("mirrored preview",message)

    def test_lighting_check_is_only_suggested_when_all_core_points_are_unclear(self):
        self.frame.landmarks[[NOSE,LW,LA],3]=.2
        self.assertNotIn("lighting",visibility_message(self.frame,10,self.config))
        self.frame.landmarks[CORE,3]=.2
        self.assertIn("check the lighting",visibility_message(self.frame,10,self.config))

    def test_stale_body_reports_waiting_for_frame_instead_of_wrong_position(self):
        self.assertIn("fresh camera frame",visibility_message(self.frame,11,self.config))

    def test_crossing_camera_divider_is_not_described_as_leaving_the_image(self):
        self.frame.x_bounds=(.03,1.97)
        self.frame.landmarks[LW,0]=1.2
        self.frame.aspect=2/3
        player=PlayerManager(self.config)
        player.update(self.frame,10)
        self.assertTrue(player.valid)
        self.assertNotIn("inside the camera",player.message)

    def test_specific_lane_message_is_retained_when_player_is_absent(self):
        self.frame.landmarks=None
        self.frame.people=0
        self.frame.status="Player 2: stand fully in your half of the camera."
        self.assertEqual(visibility_message(self.frame,10,self.config),self.frame.status)


class PreviewIdentityTests(unittest.TestCase):
    def body(self,x):
        p=neutral_pose()
        p[:,0]=(p[:,0]-.5)*.65+x
        return p

    def source(self,poses):
        return TrackingFrame(10,people=len(poses),poses=poses)

    def test_lane_labels_follow_hip_positions_when_detector_order_reverses(self):
        left,right=self.body(.25),self.body(.75)
        first=labelled_bodies(self.source([left,right]),True)
        second=labelled_bodies(self.source([right,left]),True)
        lookup=lambda rows:{round(float(np.mean(p[[LH,RH],0])),2):label for label,_,p in rows}
        self.assertEqual(lookup(first),lookup(second))
        self.assertEqual(lookup(second),{.25:"P1 / LEFT",.75:"P2 / RIGHT"})

    def test_only_right_player_is_labelled_player2(self):
        bodies=labelled_bodies(self.source([self.body(.75)]),True)
        self.assertEqual(bodies[0][0],"P2 / RIGHT")

    def test_overlapping_bodies_are_not_given_confident_player_ids(self):
        bodies=labelled_bodies(self.source([self.body(.49),self.body(.51)]),True)
        self.assertTrue(all(label=="SEPARATE / OWN LANE" for label,_,_ in bodies))

    def test_unclear_hips_cannot_assign_a_player_lane(self):
        p=self.body(.75)
        p[[LH,RH],3]=.2
        self.assertEqual(labelled_bodies(self.source([p]),True)[0][0],"HIPS UNCLEAR")

    def test_overlay_respects_aspect_fitted_image_rect_and_restores_clip(self):
        os.environ.setdefault("SDL_VIDEODRIVER","dummy")
        os.environ.setdefault("SDL_AUDIODRIVER","dummy")
        import pygame
        pygame.font.init()
        image_rect=pygame.Rect(65,31,160,120)
        canvas=pygame.Surface((300,200))
        canvas.fill((0,0,0))
        original_clip=canvas.get_clip()
        p=self.body(.25)
        p[NOSE,:2]=[float("nan"),.1]
        source=self.source([p,self.body(.75)])
        unchanged=source.poses[1].copy()
        draw_tracking_overlay(canvas,image_rect,source,True,10)
        pixels=pygame.surfarray.array3d(canvas)
        mask=np.zeros((300,200),bool)
        mask[image_rect.left:image_rect.right,image_rect.top:image_rect.bottom]=True
        self.assertTrue(np.any(pixels[mask]))
        self.assertFalse(np.any(pixels[~mask]))
        self.assertEqual(canvas.get_clip(),original_clip)
        np.testing.assert_array_equal(source.poses[1],unchanged)


if __name__=="__main__":
    unittest.main()
